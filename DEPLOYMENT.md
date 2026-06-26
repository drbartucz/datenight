# Twin Cities Date Night Portal - Deployment Guide

This project is now structured as a **FastAPI web application** that serves a beautiful, responsive dark-mode dashboard. It can be hosted on **Railway**, self-hosted on your own server (Docker / VPS), or run locally.

---

## 1. Running Locally

To run the web app on your local machine:

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the FastAPI server:
   ```bash
   python main.py
   ```
   *Alternatively:*
   ```bash
   uvicorn main:app --reload
   ```
3. Open your browser and navigate to: `http://localhost:8000`

---

## 2. Deploying on Railway

Railway is the easiest cloud provider to host this application. It detects python and container files automatically.

### Steps:
1. **Push your code to GitHub**: Create a repository and push this project directory.
2. **Deploy on Railway**:
   - Go to [Railway.app](https://railway.app) and sign in.
   - Click **New Project** &rarr; **Deploy from GitHub repo**.
   - Select your repository.
3. **Configure Environment Variables**:
   - In your Railway project dashboard, select the service.
   - Click on the **Variables** tab.
   - Add your Gemini API Key:
     - **Key**: `GEMINI_API_KEY`
     - **Value**: `[Your Actual Gemini API Key]`
4. **Deploy**:
   - Railway will read the `Dockerfile` (or `requirements.txt` via Nixpacks), install dependencies, bind to the correct `$PORT` automatically, and assign you a public URL.

---

## 3. Self-Hosting on Your Own Server (Docker / VPS)

Since a `Dockerfile` is included in the project, you can deploy it as a containerized service anywhere.

### Build and Run with Docker:
1. Build the Docker image:
   ```bash
   docker build -t datenight-portal .
   ```
2. Run the container:
   ```bash
   docker run -d -p 8000:8000 -e GEMINI_API_KEY="your_api_key_here" datenight-portal
   ```
3. Access the web app at `http://your-server-ip:8000`

### Running with PM2 / Systemd (Without Docker):
If you want to run it directly on a VPS (Ubuntu/Debian):
1. Install Python 3.12+ and system packages.
2. Clone the repository and set up a virtual environment.
3. Use a process manager like **PM2** to keep the server alive:
   ```bash
   pm2 start "uvicorn main:app --host 0.0.0.0 --port 8000" --name datenight-portal
   ```
4. Set up an Nginx reverse proxy to forward traffic from port `80` (HTTP) or `443` (HTTPS) to `http://localhost:8000`.
