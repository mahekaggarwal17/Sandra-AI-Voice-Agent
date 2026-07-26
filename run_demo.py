import os
import sys
import subprocess
import time

def main():
    print("=" * 70)
    print(" 🚀 SANDRA AI VOICE AGENT - INSTANT PUBLIC DEMO LAUNCHER")
    print("=" * 70)
    
    port = int(os.getenv("PORT", 5000))
    
    # Try pyngrok if installed
    public_url = None
    try:
        from pyngrok import ngrok
        tunnel = ngrok.connect(port)
        public_url = tunnel.public_url
        if public_url.startswith("http://"):
            public_url = public_url.replace("http://", "https://")
    except Exception as e:
        print(f"[Notice] pyngrok automatic tunnel notice: {e}")
    
    print("\nStarting local server on port 5000...")
    server_process = subprocess.Popen([sys.executable, "api_server.py"])
    
    time.sleep(2)
    
    print("\n" + "=" * 70)
    if public_url:
        print(f" ✨ PUBLIC DEMO LINK (Share with anyone on Mobile or Laptop):")
        print(f" 📱 {public_url}")
    else:
        print(" 📱 TO SHARE A PUBLIC DEMO LINK WITH ANY MOBILE PHONE:")
        print(" Option 1: Run 'npx localtunnel --port 5000' or 'ngrok http 5000'")
        print(" Option 2: Deploy to Render / Vercel / Railway using git push!")
        print(f" Local Access: http://localhost:{port}")
    print("=" * 70 + "\n")
    
    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\nStopping demo server...")
        server_process.terminate()

if __name__ == "__main__":
    main()
