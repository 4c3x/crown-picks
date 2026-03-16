# 📱 Install Crown Picks on Android

## Prerequisites
1. Make sure your Flask app is running on your PC
2. Your Android device must be on the **same WiFi network** as your PC

## Step 1: Find Your PC's IP Address

Run this command on your PC:
```powershell
ipconfig
```

Look for **IPv4 Address** under your WiFi adapter (usually something like `192.168.1.x`)

Example output:
```
Wireless LAN adapter Wi-Fi:
   IPv4 Address. . . . . . . . . . . : 192.168.1.100
```

## Step 2: Update Flask to Allow External Connections

In your `app.py`, at the bottom where it says:
```python
if __name__ == '__main__':
    app.run(debug=True)
```

Change it to:
```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
```

Then restart your Flask server.

## Step 3: Access from Android

1. Open **Chrome** on your Android phone
2. Go to: `http://YOUR_PC_IP:5000` (replace YOUR_PC_IP with the IP from Step 1)
   - Example: `http://192.168.1.100:5000`
3. You should see the Crown Picks app

## Step 4: Install as App

### Method 1: Chrome Install Prompt
1. When you visit the site, Chrome may show an "Add to Home Screen" prompt
2. Tap **Install** or **Add to Home Screen**
3. The app will be installed like a native app

### Method 2: Manual Installation
1. In Chrome, tap the **3 dots menu** (⋮) in the top right
2. Tap **"Add to Home screen"** or **"Install app"**
3. Choose a name (default: "Crown Picks")
4. Tap **Add**

### Method 3: Share Menu
1. Tap the **Share** button
2. Select **"Add to Home Screen"**
3. Tap **Add**

## Step 5: Use the App

1. Find the **Crown Picks** icon on your home screen (with the 👑 icon)
2. Tap it to launch the app in fullscreen mode
3. It will work like a native Android app!

## Features
✅ **Offline Support**: Service worker caches data for offline use  
✅ **Full Screen**: Opens without browser UI  
✅ **Fast**: Optimized for mobile performance  
✅ **Installable**: Acts like a native app  

## Troubleshooting

### Can't connect from phone?
- **Check firewall**: Windows Firewall might be blocking port 5000
  - Go to: Windows Defender Firewall → Allow an app
  - Add Python or allow port 5000
- **Wrong network**: Ensure phone and PC are on same WiFi
- **Check IP**: Make sure you're using the correct IP address

### No install prompt?
- Make sure you're using **Chrome** (not Firefox or other browsers)
- Try accessing via HTTPS (you may need to deploy to a server)
- Clear browser cache and try again

### App not updating?
- In Chrome settings, go to **Site Settings** → **Crown Picks**
- Clear storage and reload

## Cloud Deployment (Optional)

For access from anywhere (not just home WiFi), deploy to:
- **Render** (free tier): https://render.com
- **Railway** (free tier): https://railway.app
- **PythonAnywhere** (free tier): https://www.pythonanywhere.com

Then access from `https://your-app.render.com` on any device!

---

🎯 **Pro Tip**: Bookmark this as a tab on your Android browser for quick access before installing!
