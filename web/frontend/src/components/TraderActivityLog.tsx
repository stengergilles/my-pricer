import React, { useState, useEffect, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import {
  Paper,
  Typography,
  List,
  ListItem,
  ListItemText,
  Chip,
  Box,
  Collapse,
  IconButton,
} from '@mui/material';
import { ExpandMore, ExpandLess } from '@mui/icons-material';

interface Activity {
  timestamp: string;
  stage: string;
  message: string;
  crypto_id?: string;
  details?: any;
}

const stageColors: { [key: string]: string } = {
  Lifecycle: '#8e44ad',
  Discovery: '#2980b9',
  Analysis: '#f39c12',
  Strategy: '#d35400',
  Data: '#7f8c8d',
  Signal: '#27ae60',
  Decision: '#c0392b',
  Monitoring: '#16a085',
};

const ActivityItem: React.FC<{ activity: Activity }> = ({ activity }) => {
  const [expanded, setExpanded] = useState(false);
  const hasDetails = activity.details && Object.keys(activity.details).length > 0;

  const toggleExpand = () => {
    if (hasDetails) {
      setExpanded(!expanded);
    }
  };

  return (
    <ListItem
      sx={{
        borderLeft: `4px solid ${stageColors[activity.stage] || '#bdc3c7'}`, 
        mb: 1,
        alignItems: 'flex-start',
        flexDirection: 'column',
        backgroundColor: 'rgba(0, 0, 0, 0.02)',
        borderRadius: '4px',
      }}
    >
      <Box sx={{ width: '100%', cursor: hasDetails ? 'pointer' : 'default' }} onClick={toggleExpand}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <Box>
            <Chip
              label={activity.stage}
              size="small"
              sx={{ backgroundColor: stageColors[activity.stage] || '#bdc3c7', color: 'white', mr: 1, fontWeight: 'bold' }}
            />
            {activity.crypto_id && <Chip label={activity.crypto_id} size="small" variant="outlined" sx={{ mr: 1 }} />}
            <Typography variant="body2" component="span" sx={{ fontWeight: 500 }}>
              {activity.message}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
              {new Date(activity.timestamp).toLocaleTimeString()}
            </Typography>
            {hasDetails && (
              <IconButton size="small">
                {expanded ? <ExpandLess /> : <ExpandMore />}
              </IconButton>
            )}
          </Box>
        </Box>
      </Box>
      {hasDetails && (
        <Collapse in={expanded} timeout="auto" unmountOnExit sx={{ width: '100%' }}>
          <Paper elevation={0} sx={{ mt: 1, p: 1.5, backgroundColor: 'rgba(0, 0, 0, 0.03)' }}>
            <Typography variant="caption" component="pre" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
              {JSON.stringify(activity.details, null, 2)}
            </Typography>
          </Paper>
        </Collapse>
      )}
    </ListItem>
  );
};

const TraderActivityLog: React.FC = () => {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const socketRef = useRef<Socket | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    const socket = io(process.env.REACT_APP_API_URL || 'http://localhost:5000');
    socketRef.current = socket;

    socket.on('connect', () => {
      setIsConnected(true);
    });

    socket.on('disconnect', () => {
      setIsConnected(false);
    });

    socket.on('trader_activity', (data: Activity) => {
      setActivities(prev => [data, ...prev.slice(0, 99)]); // Keep last 100 activities
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  useEffect(() => {
    // Auto-scroll to top when new activity arrives
    if (listRef.current) {
      listRef.current.scrollTop = 0;
    }
  }, [activities]);

  return (
    <Paper elevation={3} sx={{ p: 2, mt: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="h6">Trader Activity Log</Typography>
        <Chip
          label={isConnected ? 'Connected' : 'Disconnected'}
          color={isConnected ? 'success' : 'error'}
          size="small"
        />
      </Box>
      <List
        ref={listRef}
        sx={{
          height: '400px',
          overflowY: 'auto',
          bgcolor: 'background.paper',
          borderRadius: '4px',
          border: '1px solid rgba(0, 0, 0, 0.08)',
        }}
      >
        {activities.length === 0 && (
          <ListItem>
            <ListItemText primary="Waiting for trader activity..." sx={{ textAlign: 'center', color: 'text.secondary' }} />
          </ListItem>
        )}
        {activities.map((activity, index) => (
          <ActivityItem key={index} activity={activity} />
        ))}
      </List>
    </Paper>
  );
};

export default TraderActivityLog;
