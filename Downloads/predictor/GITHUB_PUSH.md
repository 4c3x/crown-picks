# 🚀 Push Crown Picks to GitHub

## Step 1: Create a New GitHub Repository

1. Go to https://github.com/new
2. Repository name: `crown-picks` (or any name you prefer)
3. Description: "Elite Basketball Predictor - 80%+ accuracy predictions for all leagues worldwide"
4. Choose **Public** or **Private**
5. **DO NOT** check "Initialize with README" (you already have files)
6. Click **Create repository**

## Step 2: Push Your Code

After creating the repo, GitHub will show you commands. Use these in your terminal:

```powershell
# Remove old remote (pointing to DiasporaHub)
git remote remove origin

# Add your new Crown Picks repository
git remote add origin https://github.com/YOUR_USERNAME/crown-picks.git

# Create and switch to main branch
git branch -M main

# Push your code
git push -u origin main
```

**Replace `YOUR_USERNAME` with your actual GitHub username!**

## Step 3: Verify

Go to `https://github.com/YOUR_USERNAME/crown-picks` and you should see all your files!

---

## Quick Commands (Copy & Paste)

After you create the repo on GitHub, tell me your username and I can run the commands for you, or just copy these:

```powershell
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/crown-picks.git
git branch -M main
git push -u origin main
```

---

## ✅ What's Included

Your repo will have:
- ✅ Full Crown Picks app with PWA support
- ✅ Mobile-responsive design
- ✅ Team Points & Total Points predictions
- ✅ API clients and prediction engine
- ✅ Installation guides (ANDROID_INSTALL.md, PWA_SETUP.md)
- ✅ All icons and static files
- ✅ Requirements.txt for easy deployment

Ready to deploy to Render/Railway once it's on GitHub!
