
const REMOTE_LOGGING_ENDPOINT = process.env.REACT_APP_REMOTE_LOGGING_ENDPOINT || 'http://localhost:5000/api/log';

export const setupRemoteLogger = () => {
  const originalConsoleLog = console.log;
  const originalConsoleError = console.error;
  const originalConsoleWarn = console.warn;

  const sendLog = (level: string, message: any[]) => {
    try {
      fetch(REMOTE_LOGGING_ENDPOINT, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ level, message: JSON.stringify(message) }),
      });
    } catch (error) {
      // Fallback to original console if remote logging fails
      originalConsoleError('Failed to send remote log:', error);
    }
  };

  console.log = (...args: any[]) => {
    originalConsoleLog(...args);
    sendLog('log', args);
  };

  console.error = (...args: any[]) => {
    originalConsoleError(...args);
    sendLog('error', args);
  };

  console.warn = (...args: any[]) => {
    originalConsoleWarn(...args);
    sendLog('warn', args);
  };
};
