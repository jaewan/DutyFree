// SPDX-License-Identifier: GPL-2.0
/*
 * cxl_memtype_RECONSTRUCTED.c — /dev/cxl_wc and /dev/cxl_uc.
 *
 * RECONSTRUCTION, 2026-08-24. The original module that provided these devices
 * is lost: `benchmarks/e2e/instrument/src/common.h` defines the paths, the
 * aggressor's `wc_ntdqa` and `uc_load` modes mmap them, the paper's E1
 * dissociation depends on them, and no source, no .ko, and no loaded module
 * survives on any host. See experiments/asplos/E1_ARM_IDENTITY_AUDIT_2026-08-24.md
 * and the W4.3 ledger's Correction 2.
 *
 * This is therefore NOT the original. It is written to the description the paper
 * gives ("the WC path uses pgprot_writecombine with MOVNTDQA") and to the
 * interface the committed user-space half already expects. Numbers produced with
 * it must be reported as a re-measurement, never as a reproduction of the
 * original apparatus, and the registered check is whether they agree with the
 * frozen figures (E1 tax 1.2877x / 0.9996x; single-core WB 12.43 / WC 3.20 GB/s).
 *
 * What it does: exposes a physical address range — intended to be the CXL
 * expander's range, which appears as a cpuless NUMA node — as a character
 * device whose mmap applies a chosen cache attribute:
 *     /dev/cxl_wc  pgprot_writecombine()   (PAT WC)
 *     /dev/cxl_uc  pgprot_noncached()      (PAT UC)
 * The WB arm needs no module: it mmaps ordinary cacheable memory on the same
 * node, which is what `wb_load` already does.
 *
 * Parameters (both required; no defaults, deliberately):
 *     base=<phys addr>   len=<bytes>
 * Derive them from /proc/iomem for the CXL window rather than guessing;
 * load_cxl_memtype.sh does that and refuses if the range is not there.
 *
 * Safety: the range is validated against iomem at load time via
 * region_intersects(), mappings are capped at len, and the device is 0400 root-
 * only. This maps physical memory and is a measurement tool for our own hosts;
 * it is not intended for, and should not be shipped in, anything else.
 */
#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/fs.h>
#include <linux/mm.h>
#include <linux/io.h>
#include <linux/miscdevice.h>
#include <linux/uaccess.h>

static unsigned long base;
static unsigned long len;
module_param(base, ulong, 0444);
MODULE_PARM_DESC(base, "physical base address of the range to expose (required)");
module_param(len, ulong, 0444);
MODULE_PARM_DESC(len, "length in bytes of the range to expose (required)");

enum { ATTR_WC, ATTR_UC };

static int memtype_mmap(struct file *f, struct vm_area_struct *vma, int attr)
{
	unsigned long size = vma->vm_end - vma->vm_start;
	unsigned long off = vma->vm_pgoff << PAGE_SHIFT;

	if (off >= len || size > len - off)
		return -EINVAL;

	/* The whole point of the module: choose the cache attribute explicitly. */
	if (attr == ATTR_WC)
		vma->vm_page_prot = pgprot_writecombine(vma->vm_page_prot);
	else
		vma->vm_page_prot = pgprot_noncached(vma->vm_page_prot);

	vm_flags_set(vma, VM_IO | VM_DONTEXPAND | VM_DONTDUMP);

	return remap_pfn_range(vma, vma->vm_start,
			       (base + off) >> PAGE_SHIFT,
			       size, vma->vm_page_prot);
}

static int wc_mmap(struct file *f, struct vm_area_struct *v) { return memtype_mmap(f, v, ATTR_WC); }
static int uc_mmap(struct file *f, struct vm_area_struct *v) { return memtype_mmap(f, v, ATTR_UC); }

static const struct file_operations wc_fops = { .owner = THIS_MODULE, .mmap = wc_mmap };
static const struct file_operations uc_fops = { .owner = THIS_MODULE, .mmap = uc_mmap };

static struct miscdevice wc_dev = {
	.minor = MISC_DYNAMIC_MINOR, .name = "cxl_wc", .fops = &wc_fops, .mode = 0400,
};
static struct miscdevice uc_dev = {
	.minor = MISC_DYNAMIC_MINOR, .name = "cxl_uc", .fops = &uc_fops, .mode = 0400,
};

static int __init cxl_memtype_init(void)
{
	int rc;

	if (!base || !len) {
		pr_err("cxl_memtype: base= and len= are both required; refusing to load\n");
		return -EINVAL;
	}
	if ((base | len) & ~PAGE_MASK) {
		pr_err("cxl_memtype: base and len must be page aligned\n");
		return -EINVAL;
	}
	/* Refuse a range that is not actually device/reserved memory. A typo here
	 * would otherwise hand out a WC alias of ordinary system RAM, which is
	 * both wrong as a measurement and unsafe. */
	if (region_intersects(base, len, IORESOURCE_SYSTEM_RAM, IORES_DESC_NONE)
	    == REGION_INTERSECTS) {
		pr_err("cxl_memtype: [%#lx,%#lx) intersects System RAM; refusing\n",
		       base, base + len);
		return -EINVAL;
	}

	rc = misc_register(&wc_dev);
	if (rc)
		return rc;
	rc = misc_register(&uc_dev);
	if (rc) {
		misc_deregister(&wc_dev);
		return rc;
	}
	pr_info("cxl_memtype: /dev/cxl_wc and /dev/cxl_uc over [%#lx,%#lx) (%lu MiB)\n",
		base, base + len, len >> 20);
	return 0;
}

static void __exit cxl_memtype_exit(void)
{
	misc_deregister(&uc_dev);
	misc_deregister(&wc_dev);
	pr_info("cxl_memtype: unloaded\n");
}

module_init(cxl_memtype_init);
module_exit(cxl_memtype_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("WC/UC character-device mappings of a physical range (reconstruction; see header)");
