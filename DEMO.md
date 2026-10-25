# 🦥 findbox: 90-Second Hackathon Demo Script

**Theme**: Slow & Steady: International Sloth Day  
**Goal**: Demonstrate how `findbox` turns digital chaos into structured, searchable peace while the user does zero work.

---

### **[0:00 - 0:25] The Chaos & Manual Search Failure**
* **Visual**: Screen recording of a chaotic `Downloads` folder packed with unreadable names: `IMG_4471.png`, `scan(3)_final_FINAL.pdf`, `receipt_oct.txt`, `chat_export.txt`.
* **Action**: Start an on-screen timer. Attempt to search for a specific recipe saved weeks ago by scrolling endlessly through image thumbnails.
* **Audio / Voiceover**:
  > *"Every computer has this graveyard: hundreds of unorganized downloads, forms, and screenshots we took 'to remember later.' Sorting this takes hours of mind-numbing effort, so we never do it. Finding anything by hand is impossible."*

---

### **[0:25 - 0:40] The Lazy Drop-In**
* **Visual**: Open the `~/SlothBox/inbox` folder. Select 10 mixed sample files (WBSEDCL electricity bill, Swiggy grocery receipt, WhatsApp landlord rent chat, Instagram paneer recipe, flight ticket, doctor prescription, tax form) and drag them in all at once.
* **Audio / Voiceover**:
  > *"Here is the entire user workflow: drag your messy files into one folder. Walk away. Go to sleep. That's literally all you have to do."*

---

### **[0:40 - 0:55] Safe Autonomous Organization**
* **Visual**: Open terminal. Run:
  ```bash
  python3 sloth_box.py run --inbox sample_data
  ```
  Highlight the dry-run output displaying proposed names (`2026-10-12_electricity-bill_WBSEDCL.txt`) and categories.  
  Then run:
  ```bash
  python3 sloth_box.py run --inbox sample_data --apply
  ```
* **Audio / Voiceover**:
  > *"Running at idle CPU priority, local open-weight Gemma 3 inspects each file. Notice the safety: it runs in dry-run mode first, never deletes anything, and logs an atomic undo history. With `--apply`, everything is filed into clean categories."*

---

### **[0:55 - 1:05] The "While You Did Nothing" Payoff**
* **Visual**: Quick cut to opening `TODO.md` and `digest.md`.
  - Highlight the `🚨 Due Soon` section: `Pay electricity bill by 2026-10-28`.
  - Highlight `digest.md` listing what moved and summary highlights.
* **Audio / Voiceover**:
  > *"Look at `TODO.md`: it automatically pulled deadlines right out of the text, flagging my electricity bill due in 3 days. And `digest.md` gives me a clear morning summary of what happened while I did nothing."*

---

### **[1:05 - 1:20] Vague-Memory Search in Airplane Mode**
* **Visual**: Open macOS menu bar and toggle **Airplane Mode (Wi-Fi OFF)**.  
  Launch web UI:
  ```bash
  python3 sloth_box.py serve
  ```
  In browser (`http://127.0.0.1:8765`), type into search box:
  > *"instagram recipe with paneer early September"*  
  Hit Enter. Instantly, `2026-09-04_04-instagram-recipe-paneer-tikka.txt` appears with tag `#recipes` and full summary.
* **Audio / Voiceover**:
  > *"Now for the twist. With Wi-Fi completely turned off, I type what I actually remember: 'instagram recipe with paneer early September'. Local Gemma extracts the intent, queries SQLite FTS5 with BM25, and brings up the exact file instantly."*

---

### **[1:20 - 1:30] Payoff Meter & The Open-Weight Close**
* **Visual**: Point cursor to the **Payoff Meter**:
  - `Estimated Time Saved: 20.0 minutes`
  - `Your Effort: 0 minutes (100% laziness)`
  - Footer: `Runs 100% on your device. No uploads. Works offline.`
* **Audio / Voiceover**:
  > *"Our Payoff Meter shows 20 minutes saved, with zero effort on your part. And because it runs entirely on open-weight Gemma on your own machine, your bank forms, chats, and medical records never touch a cloud server. Move slow. Conserve energy. Let findbox do the work."*
