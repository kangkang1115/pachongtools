module.exports = {
  apps: [
    {
      name: 'pachong-backend',
      cwd: './backend',
      script: 'server.py',
      interpreter: 'C:/Users/liyik/AppData/Local/Programs/Python/Python312/python.exe',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
    },
    {
      name: 'pachong-frontend',
      cwd: './frontend',
      script: 'node_modules/vite/bin/vite.js',
      args: '--host 0.0.0.0 --port 3000',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 5000,
    },
  ],
};
