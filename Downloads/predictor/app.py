"""

    app.run(host='0.0.0.0', debug=True, port=5000)

if __name__ == '__main__':
    import socket
    
    # Get local IP address
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "localhost"
    
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║           👑 CROWN PICKS - Elite Basketball Predictor v7 👑          ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  All leagues. All games. Top 2 picks. Min 80% probability.           ║
║                                                                      ║
║  🌐 Server Access:                                                   ║
║     • Local:   http://localhost:5000                                ║
║     • Network: http://{}:5000                               ║
║                                                                      ║
║  📱 Android App: See ANDROID_INSTALL.md for mobile setup             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """.format(local_ip))
    
    app.run(host='0.0.0.0', debug=True, port=5000)
