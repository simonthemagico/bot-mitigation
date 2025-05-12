module.exports = {
    apps: [
      {
        name: "bridge-api",
        script: "python3",
        args: "-m uvicorn api.main:app --host 0.0.0.0 --port 8000",
        cwd: "/Users/administrator/bot-mitigation/bridge",
        error_file: "./logs/bridge-api-error.log",
        out_file: "./logs/bridge-api-out.log",
        env: {
          // "MY_ENV_VAR": "some_value"
        },
        watch: false
      }, 
      {
        // New entry for cleanup logs
        name: "cleanup-logs",
        script: "python3",                    // Command to run (python)
        args: "utils/cleanup_logs.py",        // The actual script to run
        cwd: "/Users/administrator/bot-mitigation/bridge",
        interpreter: null,                    // 'null' means use 'script' directly; 
                                             // or keep 'python3' for 'interpreter'
        // Run every hour at minute 0 e.g. 20:00
        cron_restart: "0 * * * *",
        autorestart: false,                   // Don't keep it running continuously
        watch: false
      }
    ]
  };
  