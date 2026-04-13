## 📌 Overview

This repository contains experimental implementations for the paper:

**"Understanding Students Through Dialogue: A Dialogue Knowledge Tracing System for Learning Analytics"**
Accepted at [ProActLLM](https://proactllm.github.io/#accepted-papers)

A related thesis version is available here:
👉 https://etd.lib.ncu.edu.tw/detail/2ed71350cc8bca40569b03ad801126fa/

*Note: The thesis version may differ from the accepted conference version.*

The experiments focus on integrating retrieval-augmented generation (RAG), knowledge graph construction, and dialogue-based knowledge tracing for modeling student learning.

---

## 🧪 Experiments

The main experimental workflow is provided in:

notebooks/experiment.ipynb

This notebook demonstrates the end-to-end experimental pipeline.

Core functionalities are implemented in:

src/main.py

---

## ⚠️ Notes on Reproducibility

This repository focuses on experimental workflows and is **not fully self-contained**.

* The complete environment and datasets used in the paper are not publicly available.
* Some components depend on external services and private data.

To run the system, a LightRAG server is required to handle course data:

👉 https://github.com/BlackWaterGua/ConversaionKT

Please follow the setup instructions in that repository before running the experiments.

This repository mainly provides the experimental pipeline and core logic for reference.

---

## 🙏 Acknowledgement

This project is based on the original LightRAG repository:

👉 https://github.com/HKUDS/LightRAG
