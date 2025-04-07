graph TD
    subgraph User Interaction
        User[User (Admin)] -- Interacts via Browser --> Browser[Browser]
        Browser -- HTTP Request --> Nginx[Nginx Reverse Proxy]
    end

    subgraph Network Monitor Host (Pi)
        Nginx -- Serves Static Files --> Frontend[React Frontend (in Browser)]
        Nginx -- Proxies API Request (/api/v1) --> Backend[Flask/Gunicorn Backend (Web Service)]
        Frontend -- API Call --> Nginx

        Backend -- Read/Write --> DB[(Database SQLite)]
        Backend -- Uses --> Controller{Device Controller}

        Controller -- Selects SSH --> SSHController[SSHDeviceController]
        SSHController -- Uses --> SSH[SSH Manager (Paramiko)]

        Syslog[Syslog Listener (UDP 514 Service)] -- Stores Parsed Log --> DB

        AIPusher[AI Pusher (Scheduler)] -- Runs periodically --> Backend
        AIPusher -- Reads Logs --> DB
        AIPusher -- Pushes Formatted Logs (HTTPS) --> AIEngine[Remote AI Engine]
    end

    subgraph Remote Systems
        OpenWRT[OpenWRT Device(s)] -- Sends Syslog UDP --> Syslog
        OpenWRT -- SSH Connection --> SSH
        AIEngine
    end

    %% Specific Flows
    Browser -- View Logs/Devices --> Nginx
    Browser -- Control Action (Reboot, Config) --> Nginx
    SSH -- Executes Command (UCI, reboot, status) --> OpenWRT