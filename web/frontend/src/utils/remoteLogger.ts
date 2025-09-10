
const REMOTE_LOGGING_ENDPOINT = process.env.REACT_APP_REMOTE_LOGGING_ENDPOINT || `${process.env.REACT_APP_API_URL || 'http://localhost:5000'}/api/log`;

export const setupRemoteLogger = (getAccessToken?: () => Promise<string | undefined>) => {
  const originalConsoleLog = console.log;
  const originalConsoleError = console.error;
  const originalConsoleWarn = console.warn;

  const sendLog = async (level: string, message: any[]) => {
    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json',
      };

      if (getAccessToken) {
        const token = await getAccessToken();
        if (token) {
          (headers as Record<string, string>).Authorization = `Bearer ${token}`;
        }
      }

      fetch(REMOTE_LOGGING_ENDPOINT, {
        method: 'POST',
        headers: headers,
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
