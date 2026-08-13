Pipeline order matches `main.py` / `diagnose_system()`: GAE → HND → FDM,
then feed back. (`transition.py` is a standalone simulator on the side.)

```
┌─────────────────────────────────────────────────────────────┐
│                    SYSTEM INPUT                            │
│  (Nodes, Edges, Dependencies, Environmental Variables)     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         Geometric Applicability Engine (GAE)               │
│  - Calculates C (Cycle Density), N (Critical Nodes),       │
│    L (Linearity), R (Recursive Variance)                   │
│  - Scores all geometries (Line, Triangle, Tetrahedron,     │
│    Torus, Icosahedron, Fractal)                            │
│  - Outputs: Recommended geometry + full scoreboard         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           Hidden Node Detector (HND)                       │
│  - Compares predicted vs. actual output                    │
│  - Detects residual patterns (unmodeled loss)              │
│  - Identifies phantom causality (hidden mediators)         │
│  - Detects negative space (hidden buffers)                 │
│  - Outputs: Suggested new nodes to add                     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            Fractal Dependency Mapper (FDM)                 │
│  - Traces any node to primitive roots                      │
│  - Identifies branching depth and redundancy               │
│  - Outputs: Dependency tree, Root set, Branch health       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    FEEDBACK LOOP                           │
│  - Update model with new nodes                             │
│  - Re-run GAE                                              │
│  - Re-run HND                                              │
│  - Iterate until residuals fall below threshold            │
└─────────────────────────────────────────────────────────────┘
```
