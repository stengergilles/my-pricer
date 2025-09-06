import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  IconButton,
  Grid,
  CircularProgress
} from '@mui/material';
import { Stop } from '@mui/icons-material';
import { useApiClient } from '../hooks/useApiClient.ts';
import { useQuery } from '@tanstack/react-query';
import { Crypto } from '../utils/types';

export const ScheduleTab = () => {
  const { getJobs, scheduleJob, deleteJob, getJobLogs, apiClient, getCryptos } = useApiClient();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [jobLogs, setJobLogs] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  // Form state
  const [jobType, setJobType] = useState('optimize_crypto');
  const [crypto, setCrypto] = useState('');
  const [interval, setInterval] = useState(60);

  const { data: volatileCryptos, isLoading: cryptosLoading } = useQuery<Crypto[]>({
    queryKey: ['volatileCryptos'],
    queryFn: () => getCryptos({ volatile: true, min_volatility: 20.0, limit: 250 }).then(data => data.cryptos),
    enabled: !!apiClient,
  });

  useEffect(() => {
    const fetchJobs = async () => {
      
      try {
        const response = await getJobs();
        setJobs(response);
        setError('');
      } catch (err) {
        setError('Failed to fetch jobs');
        setJobs([]);
      }
    };
    
    if (apiClient) { // Check if apiClient is initialized
      fetchJobs();
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [apiClient]); // Depend on apiClient

  const handleJobClick = async (jobId: string) => {
    if (expandedJobId === jobId) {
      setExpandedJobId(null);
      setJobLogs([]);
    } else {
      setExpandedJobId(jobId);
      setLogsLoading(true);
      try {
        const response = await getJobLogs(jobId);
        setJobLogs(response.logs || []);
        setError('');
      } catch (err) {
        setError('Failed to fetch job logs');
        setJobLogs([]);
      } finally {
        setLogsLoading(false);
      }
    }
  };

  const submitJob = async () => {
    if (!crypto) {
      setError('Crypto is required');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');
    
    try {
      await scheduleJob({
        function: jobType,
        trigger: 'interval',
        trigger_args: { seconds: interval },
        func_args: [crypto]
      });
      
      setSuccess('Job scheduled successfully');
      setCrypto('');
      
      // Refetch jobs
      try {
        const response = await getJobs();
        setJobs(response);
      } catch (err) {
        // Ignore refetch errors
      }
    } catch (err) {
      setError('Failed to schedule job');
    } finally {
      setLoading(false);
    }
  };

  const stopJob = async (jobId) => {
    setError('');
    setSuccess('');
    try {
      await deleteJob(jobId);
      setSuccess('Job stopped');
      
      // Refetch jobs
      try {
        const response = await getJobs();
        setJobs(response);
      } catch (err) {
        // Ignore refetch errors
      }
    } catch (err) {
      setError('Failed to stop job');
    }
  };

  return (
    <Box sx={{ p: 2 }}>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

      <Grid container spacing={3}>
        {/* Submit Job Form */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Schedule New Job</Typography>
              
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel id="job-type-label">Job Type</InputLabel>
                <Select
                  labelId="job-type-label"
                  value={jobType}
                  label="Job Type"
                  onChange={(e) => setJobType(e.target.value)}
                >
                  <MenuItem value="optimize_crypto">Optimize Crypto</MenuItem>
                </Select>
              </FormControl>

              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel id="crypto-label">Crypto</InputLabel>
                <Select
                  labelId="crypto-label"
                  value={crypto}
                  label="Crypto"
                  onChange={(e) => setCrypto(e.target.value)}
                  disabled={cryptosLoading}
                >
                  {cryptosLoading ? (
                    <MenuItem value="">
                      <CircularProgress size={20} />
                      <Typography sx={{ ml: 1 }}>Loading...</Typography>
                    </MenuItem>
                  ) : (
                    volatileCryptos?.map((c) => (
                      <MenuItem key={c.id} value={c.id}>
                        {c.name} ({c.symbol.toUpperCase()})
                      </MenuItem>
                    ))
                  )}
                </Select>
              </FormControl>

              <TextField
                fullWidth
                type="number"
                label="Interval (seconds)"
                value={interval}
                onChange={(e) => setInterval(Number(e.target.value))}
                sx={{ mb: 2 }}
              />

              <Button
                variant="contained"
                onClick={submitJob}
                disabled={loading}
                fullWidth
              >
                {loading ? 'Scheduling...' : 'Schedule Job'}
              </Button>
            </CardContent>
          </Card>
        </Grid>

        {/* Active Jobs */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Active Jobs</Typography>
              
              {jobs.length === 0 ? (
                <Typography color="text.secondary">No active jobs</Typography>
              ) : (
                jobs.map((job) => (
                  <Box key={job.id} sx={{ 
                    display: 'flex', 
                    flexDirection: 'column',
                    justifyContent: 'space-between', 
                    alignItems: 'flex-start',
                    p: 2,
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: 1,
                    mb: 1,
                    cursor: 'pointer'
                  }} onClick={() => handleJobClick(job.id)}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', width: '100%' }}>
                      <Box>
                        <Typography variant="subtitle2">{job.name || job.id}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          Next: {job.next_run_time}
                        </Typography>
                      </Box>
                      <IconButton 
                        color="error" 
                        onClick={(e) => { e.stopPropagation(); stopJob(job.id); }}
                        size="small"
                      >
                        <Stop />
                      </IconButton>
                    </Box>
                    {expandedJobId === job.id && (
                      <Box sx={{ mt: 2, width: '100%' }}>
                        <Typography variant="subtitle2">Job Logs:</Typography>
                        {logsLoading ? (
                          <Typography>Loading logs...</Typography>
                        ) : jobLogs.length > 0 ? (
                          <Box sx={{ 
                            backgroundColor: '#f0f0f0',
                            p: 1,
                            borderRadius: 1,
                            maxHeight: 200,
                            overflowY: 'auto',
                            whiteSpace: 'pre-wrap',
                            wordBreak: 'break-all'
                          }}>
                            {jobLogs.map((log, index) => (
                              <Typography key={index} variant="caption" component="pre" sx={{ margin: 0 }}>
                                {log}
                              </Typography>
                            ))}
                          </Box>
                        ) : (
                          <Typography variant="caption" color="text.secondary">No logs available.</Typography>
                        )}
                      </Box>
                    )}
                  </Box>
                ))
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};
