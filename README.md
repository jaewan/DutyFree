# DutyFree: Disentangling Coherence from Prefetching for Disaggregated Memory

DutyFree is an end-to-end implementation of the **"STREAMING"** memory type contract.

This repository serves as the **Umbrella Repository** for the project, coordinating the OS-side implementation in the Linux kernel and the architecture-side implementation in the gem5 simulator.

## 1. Project Overview: The Directory Tax

Current x86 architectures suffer from a **prefetcher-directory coupling**. To sustain high bandwidth over high-latency CXL fabrics (200-500ns), hardware stream prefetchers are required. However, these prefetchers only activate for **Write-Back (WB)** pages, which unconditionally enroll every fetched line into the socket's coherence directory (e.g., Intel Snoop Filter, AMD Probe Filter).

For read-only, immutable CXL data (Write-Once-Read-Many), this enrollment is a "tax"—it consumes expensive on-die SRAM metadata capacity for data that will never be invalidated. This causes:
* **Silent Performance Interference**: Directory overflows cause back-invalidations that evict local cache lines, inflating co-located application latency by up to **28%**.
* **No Existing Remedy**: Standard mechanisms like Cache Allocation Technology (CAT) or Write-Combining (WC) fail because they either don't control the metadata path or disable prefetchers, dropping bandwidth by ~4x.

**DutyFree** implements the **STREAMING** contract: a new page-table memory type where:
1. **The OS** guarantees read-only access and type uniformity at the VMA level.
2. **The Hardware** preserves high-performance prefetch activation while bypassing coherence directory enrollment.

## 2. Repository Structure

This project uses Git Submodules to manage the large codebases of Linux and gem5 without polluting their respective histories.

```text
DutyFree/ (Umbrella)
├── linux/           # [Submodule] DutyFree-Linux: X86 PAT & VMA integration
├── gem5/            # [Submodule] DutyFree-Gem5: Page walker & directory bypass logic
├── workloads/       # OLAP/KV-cache benchmarks
├── scripts/         # Integrated build and simulation orchestration
└── docs/            # Hardware-Software Interface Contract specifications
```

## 3. Getting Started

### Prerequisites
* x86_64 Build Essentials
* scons (for gem5)

### Initializing the Project
```bash
git clone --recursive https://github.com/your-org/DutyFree.git
cd DutyFree
```

### Building the Components
* **Linux Kernel**:
  ```bash
  cd linux
  make dutyfree_defconfig
  make -j$(nproc)
  ```
* **gem5**:
  ```bash
  cd gem5
  scons build/X86/gem5.opt -j$(nproc)
  ```
