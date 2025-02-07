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
      }
    ]
  };
  