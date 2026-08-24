# Out-of-tree build for the reconstructed cxl_wc/cxl_uc module.
# See cxl_memtype_RECONSTRUCTED.c's header: this is a reconstruction, not the
# original apparatus, and numbers from it are re-measurements.
obj-m += cxl_memtype_RECONSTRUCTED.o
KDIR ?= /lib/modules/$(shell uname -r)/build

all:
	$(MAKE) -C $(KDIR) M=$(PWD) modules

clean:
	$(MAKE) -C $(KDIR) M=$(PWD) clean
