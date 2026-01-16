# 🧠👓 Memento  
### A Memory-Support System for Dementia Patients Powered by Voice, Vision, and AI

Memento is an assistive technology platform designed to support individuals living with dementia by helping them recognize familiar faces, remember recent conversations, and reduce daily anxiety caused by memory loss.

By combining **smart glasses**, **real-time facial recognition**, **voice transcription with speaker diarization**, and **AI-powered caregiver assistance**, Memento functions as an external, supportive memory layer. It operates passively in the background while preserving the user’s dignity, autonomy, and independence.

---

## 💡 Inspiration

Dementia patients often struggle not just with forgetting facts, but with forgetting **people** — faces, names, relationships — and **recent interactions**. This leads to confusion, repeated questions, and emotional distress for both patients and caregivers.

We were inspired by a simple but powerful question:

> **What if technology could quietly help someone remember who they’re talking to, and what just happened, without requiring effort or technical skill?**

Rather than building another reminder app, Memento focuses on **human signals**: faces and voices. Memory support should be **passive, contextual, and empathetic**, especially for cognitively vulnerable users.

---

## 🛠️ What It Does

Memento is composed of **three tightly integrated systems**:

---

### 🧑‍💻 1. Dynamic Web Application (Memory Management)

**Tech Stack:**  
- Frontend: **Next.js**  
- Backend: **Flask (Python)**  
- Database: **MongoDB**  
- APIs: **RESTful**

**Features:**
- Secure user authentication
- Personal memory space for each patient
- Ability to add and manage acquaintances (family, friends, caregivers)

For each person, the system stores:
- Name  
- Relationship  
- Personal summary  
- Facial embeddings  

All data is securely stored in MongoDB as a proof of concept.

---

### 👓 2. Real-Time Facial Recognition (Smart Glasses Simulation)

- Smart glasses capture live video
- Faces are processed using **InsightFace**
- Facial embeddings are compared using **cosine similarity**:

\[
\text{similarity}(A, B) = \frac{A \cdot B}{|A| |B|}
\]

**When a match is found:**
- The person’s **name**, **relationship**, and **summary** are retrieved
- Information can be surfaced to the user or caregiver in real time

This helps dementia patients recognize who they are interacting with, reducing fear, confusion, and social anxiety.

---

### 🎙️ 3. Voice & Conversation Memory (Diarization + AI)

- Separate web application for real-time conversation transcription
- Built using the **Gemini API**
- Uses **speaker diarization** to identify who spoke when

**Conversations are:**
- Timestamped  
- Speaker-labeled  
- Stored for later review  

#### 🤖 Caregiver AI Assistant
A Gemini-powered caretaker agent can:
- Answer questions about recent interactions
- Provide conversation context to caregivers
- Assist in reassurance and memory recall

---

## 🧱 How We Built It

### Frontend
- **Next.js** for the patient-facing application
- Clean, accessible UI focused on simplicity and clarity
- Separate interface for conversation transcription and review

### Backend
- **Flask** servers for:
  - Facial recognition pipeline
  - Voice processing and diarization
- **MongoDB** for:
  - Facial embeddings
  - User profiles
  - Conversation transcripts
  - Speaker metadata

### AI & Machine Learning
- **InsightFace** for face detection and embedding generation
- **Cosine similarity** for fast and reliable face matching
- **Gemini API** for:
  - Speech-to-text
  - Speaker diarization
  - Caregiver conversational agent

A major portion of development time was spent tuning diarization parameters to balance:
- Over-segmentation vs. under-segmentation
- Noise robustness
- Latency vs. accuracy  

This was critical, as incorrect speaker attribution can be harmful in dementia care.

---

## ⚠️ Challenges

- Reliable facial recognition in real-world conditions (lighting, angles, motion)
- Diarization accuracy in noisy or overlapping conversations
- Latency constraints for live audio and video processing
- Designing for cognitive vulnerability where errors have emotional consequences
- Integrating vision, voice, and AI agents into a coherent system

---

## 🏆 Accomplishments

- Built a working **end-to-end system** from smart glasses to AI-powered memory recall
- Successfully integrated **InsightFace** and **Gemini** in meaningful, non-trivial ways
- Designed an assistive system for dementia patients that can also support people with everyday memory challenges
- Created a foundation suitable for extension into clinical or caregiving environments

---

## 📚 What We Learned

- Assistive technology must be **passive, forgiving, and unobtrusive**
- Facial recognition alone isn’t enough — **context matters**
- Voice AI becomes powerful only with **accurate diarization**
- Designing for dementia fundamentally changes how you think about UX, safety, and reliability
- Small technical errors can have large emotional consequences

---

## 🚀 What’s Next

- Personalized speaker identification for frequent caregivers
- Automatic conversation summaries using Gemini
- Proactive reassurance prompts  
  *(e.g., “You just spoke with your daughter.”)*
- Clinical validation and caregiver feedback
- Expanded hardware support beyond smart glasses

---

## ❤️ Final Note

**Memento isn’t about recording everything.**  
It’s about helping people remember **what matters** — and **who matters** — when memory begins to fade.
