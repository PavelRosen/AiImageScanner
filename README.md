<div align="center">
  <h1>AiImageScanner 🤖✨</h1>
</div>

Tired of squinting at thousands of photo thumbnails, desperately searching for that *one* picture of a sunset, your dog, or that weird-looking bird you saw last summer? Yeah, me too.

**AiImageScanner** is a desktop tool that lets a friendly AI do the tedious work for you. Just tell it what you're looking for (like "cat"), point it at a folder, and watch as it magically finds all the relevant images.

![App Screenshot](https://github.com/user-attachments/assets/68a35324-4abb-4dae-bfe6-b59ab3dd06d1)

---

## Table of Contents

- [Core Features](#-core-features)
- [Getting Started: Download & Run](#-getting-started-download--run)
- [Setup & Usage](#️-the-important-bit-setup--usage)
- [Support the Project](#-support-the-project)
- [About the Creator](#-about-the-creator)

---

## ✅ Core Features

-   **Flexible AI Brains:** Choose your image analyst!
    -   ☁️ **Cloud Power:** Use powerful models from Google, OpenAI (ChatGPT), and DeepSeek for maximum accuracy.
    -   🧠 **Local & Private:** Run a 100% free, private, and offline AI using **Ollama**. Your photos never leave your computer.
-   **Deep Search:** Scans folders within folders (recursively) so no image is left behind.
-   **Automatic Organizer:** Found images can be automatically copied or moved to a brand new, tidy folder.
-   **Wide Format Support:** Handles everything from standard JPGs and PNGs to professional RAW formats like CR2, DNG, and TIFF.

---

## 🚀 Getting Started: Download & Run

You can grab the latest ready-to-use version from the [**Releases Page**](https://github.com/PavelRosen/AiImageScanner/releases). No Python installation needed!

### ❖ For Windows Users

1.  Download the `AiImageScanner.exe` file from the latest release.
2.  Run it. You might see a Windows SmartScreen warning because the app isn't digitally signed (that costs money!).
3.  Just click **"More info"** and then **"Run anyway"**.

### 🐧 For Linux Users

1.  Download the `AiImageScanner` file from the latest release.
2.  Open a terminal in your download folder.
3.  You need to give the file permission to run. It's like a digital pep talk. Run this command:
    ```bash
    chmod +x AiImageScanner
    ```
4.  Now, run the app from your terminal:
    ```bash
    ./AiImageScanner
    ```

---

## 🛠️ The Important Bit: Setup & Usage

The app is simple, but to make the AI work, you have two main choices.

### Option 1: Using Cloud AI (The Easy Way)

If you want to use Google, ChatGPT, or DeepSeek, you'll need an **API Key**. First, get a key from one of the services below, then just paste it into the "API Key" field in the app, select the provider, and you're ready to scan!

#### 🔑 Where to Get API Keys

-   **Google Gemini (Google AI Studio)**
    -   This is often the easiest to get and has a generous free tier.
    -   **Direct Link:** [**https://aistudio.google.com/app/apikey**](https://aistudio.google.com/app/apikey)
    -   **Instructions:** Sign in, click "Create API key in new project", and copy the key.

-   **OpenAI (ChatGPT)**
    -   Required for models like GPT-4o.
    -   **Direct Link:** [**https://platform.openai.com/api-keys**](https://platform.openai.com/api-keys)
    -   **Instructions:** Sign up for a developer account (this is different from a regular ChatGPT account). Click "Create new secret key". **Important:** OpenAI shows the key only once, so copy it immediately. *Note: New accounts get free credits that expire.*

-   **DeepSeek**
    -   A powerful and cost-effective vision model.
    -   **Direct Link:** [**https://platform.deepseek.com/api_keys**](https://platform.deepseek.com/api_keys)
    -   **Instructions:** Create an account, click "Create new secret key", and copy it immediately. *Note: DeepSeek also provides free credits for new accounts.*

---

### Option 2: Using Local AI with Ollama (The Awesome, Private Way)

This is the coolest option. It's completely free and private. It just requires a one-time setup of a tool called **Ollama**.

**Step 1: Install Ollama**
Ollama is the engine that runs powerful AI models on your own computer.

-   Go to [**https://ollama.com**](https://ollama.com) and download the installer for your OS (Windows, Linux).
-   Run the installer. Ollama will now run quietly in the background.

**Step 2: Get a "Vision" Model**
Ollama is the engine, but you need a driver who can actually "see". LLaVA is a fantastic, popular choice.

-   Open a Terminal (or Command Prompt on Windows).
-   Run the following command. This will download the LLaVA model (it's a few gigabytes, so be patient).
    ```bash
    ollama run llava
    ```
-   Once it's done, you can close the terminal. You only need to do this once!

**Step 3: Use it in AiImageScanner!**
-   In the app, select **"ollama"** as the provider.
-   In the "Model" field, type the name of the model you downloaded: `llava`.
-   That's it! No API key needed. Start scanning!

---

## 🙏 Support the Project

If this tool saved you from a photo-sorting headache or you just think it's neat, consider showing some love! It helps fuel future development (and my caffeine addiction).

-   **☕ Buy me a coffee:** [**https://ko-fi.com/pavelrst**](https://ko-fi.com/pavelrst)
-   **₿ Send some Bitcoin:**
    ```
    BC1QM2E6SE7FUE4WEPMXU2ASM47AS59WVX4WL6WRXW
    ```

---

## 👨‍💻 About the Creator

Created with bits, bytes, and a lot of coffee by **Pavel Rosental**.

Got questions, feedback, or a great idea? Feel free to reach out:
-   **📧 Email:** [pavelrzt@gmail.com](mailto:pavelrzt@gmail.com)
