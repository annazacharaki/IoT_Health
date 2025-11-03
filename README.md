# IoT_Health

**IoT_Health** is an end-to-end IoT health monitoring system that integrates embedded hardware, biomedical sensors, signal processing, local data encryption, and a secure web application with on-device AI support.  
The project demonstrates a complete pipeline — from physiological data acquisition to encrypted storage and intelligent visualization.

---

## Overview

IoT_Health is a portable, low-cost biomedical monitoring solution built on a **Raspberry Pi 5**.  
It continuously collects health metrics such as **body temperature, heart rate, oxygen saturation (SpO₂), and ECG signals**, encrypts them locally, and visualizes real-time data through a **Flask-based dashboard**.  
A **local LLM module** enables natural-language interaction, allowing healthcare professionals to query the system privately without cloud dependency.

---

## System Architecture

```
 ┌───────────────────────────────┐
 │        Biomedical Sensors     │
 │ ┌────────────┐ ┌────────────┐ │
 │ │ MCP9808    │ │ MAX30102   │ │
 │ │ Temperature│ │ SpO₂/HR     │ │
 │ └────────────┘ └────────────┘ │
 │       ┌───────────────┐       │
 │       │ AD8232 ECG    │       │
 │       └───────────────┘       │
 └──────────────┬────────────────┘
                │  I²C / Analog (ADC3008)
 ┌──────────────▼─────────────────────────────┐
 │          Raspberry Pi 5 (Python)           │
 │  • Signal filtering & preprocessing        │
 │  • AES-128-GCM data encryption             │
 │  • SQLite local database                   │
 │  • Flask web dashboard (Chart.js, Tailwind)│
 │  • LLM Q&A module via Ollama (Qwen-2 1.5B) │
 │  • Secure remote access via LocalXpose     │
 └────────────────────────────────────────────┘
```

---

## Features

- **End-to-end IoT stack:** From sensor hardware to AI-assisted analytics  
- **Secure data flow:** AES-128-GCM encryption and local SQLite storage  
- **Autonomous operation:** systemd services auto-start Flask and LocalXpose on boot  
- **Local AI integration:** on-device Q&A module powered by Qwen-2 1.5B  
- **Modern UI:** Tailwind-styled dashboard with real-time graphs (Chart.js)  
- **Remote access:** Encrypted web tunneling via LocalXpose  
- **Portable design:** Compact, self-contained embedded system  

---

## Technologies Used

- **Hardware:** Raspberry Pi 5, MCP9808, MAX30102, AD8232, ADC3008  
- **Software:** Python 3, Flask, SQLite, systemd, LocalXpose, Ollama  
- **Libraries:** smbus2, numpy, scipy, cryptography, chart.js, tailwindcss  
- **Encryption:** AES-128-GCM, PKCS#7 padding  
- **AI Layer:** Qwen-2 1.5B local inference (Ollama)  

---

## Signal Processing

Each biomedical input is filtered and normalized prior to storage:
- **ECG:** Low-pass and moving-average filtering  
- **SpO₂:** Ratio-of-ratios computation from IR/Red intensities  
- **Temperature:** Precision I²C readings with MCP9808 calibration  
Filtered signals are then timestamped and stored securely in the local database.

---

## Database & Encryption

All sensor readings are written to **SQLite**, with each entry encrypted using **AES-128-GCM** before insertion.  
Decryption keys are stored securely in a local `.env` file and never exposed to the network.

---

## Web Dashboard

A Flask web application displays real-time and historical trends for all measured vitals.  
It supports:
- Secure login (optional)
- Graphical visualization (Chart.js)
- Instant data refresh  
- Integrated **LLM Q&A** for natural-language queries such as:
  > "Show me the last 5 ECG readings"  
  > "What was the average SpO₂ today?"

---

## Remote Access

Using **LocalXpose**, authorized healthcare professionals can access the web dashboard securely from remote devices without public IP exposure.  
The tunnel starts automatically at boot through systemd services.

---


## Project Images

| Device Overview | Sensors Close-up | Additional Views |
|------------------|------------------|------------------|
| ![Device Overview](dz_app/static/img/device_overview.jpg) | ![Sensors Close-up](dz_app/static/img/sensors_closeup.jpg) | ![Extra View 1](dz_app/static/img/sensors_extra1.jpg) |

![Extra View 2](dz_app/static/img/sensors_extra2.jpg)



---

## Security Notes
- All data remains **fully local** by default.  
- The system uses **AES-128-GCM** encryption and never transmits unencrypted signals.  
- The AI model runs **offline**, ensuring complete data privacy.  

---

## Future Work
- Integration with cloud medical record systems  
- Advanced analytics (HRV, ECG classification)  
- Multi-user management and authentication layers  
- Extended LLM capabilities for patient summaries  

---

## Author
**Anna Zacharaki**  
Integrated Master’s in Computer Engineering and Informatics  
University of Patras  
2025  

---

## LicenseCopyright (c) 2025 Anna Zacharaki

All rights reserved.

This software and its associated documentation files (the "Software") are provided for academic and research purposes only.

Permission is hereby granted, free of charge, to use, copy, and modify the Software for non-commercial academic and research use, subject to the following conditions:

1. The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
2. Commercial use, redistribution, or sale of the Software or any derivative works is strictly prohibited without the prior written consent of the author.
3. The Software is provided "as is", without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement.

In no event shall the author be liable for any claim, damages, or other liability arising from the use or inability to use the Software.

For permission requests or collaborations, please contact:  
**Anna Zacharaki** 
Email: anna.zacharaki1@gmail.com
