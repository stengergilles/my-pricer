import React, { useState, useEffect, useCallback } from 'react';
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
  Grid
} from '@mui/material';
import { Stop } from '@mui/icons-material';
import { useApiClient } from '../hooks/useApiClient.ts';

export const ScheduleTab = () => {
  const { getJobs, scheduleJob, deleteJob } = useApiClient();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  // Form state
  const [jobType, setJobType] = useState('analyze_crypto');
  const [crypto, setCrypto] = useState('');
  const [interval, setInterval] = useState(60);

  const fetchJobs = useCallback(async () => {
    try {
      const response = await getJobs();
      setJobs(response);
    } catch (err) {
      setError('Failed to fetch jobs');
    }
  }, [getJobs]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const submitJob = async () => {
    if (!crypto.trim()) {
      setError('Crypto symbol is required');
      return;
    }

    setLoading(true);
    setError('');
    
    try {
      await scheduleJob({
        function: jobType,
        trigger: 'interval',
        trigger_args: { seconds: interval },
        func_args: [crypto.toUpperCase()]
      });
      
      setSuccess('Job scheduled successfully');
      setCrypto('');
      fetchJobs();
    } catch (err) {
      setError('Failed to schedule job');
    } finally {
      setLoading(false);
    }
  };

  const stopJob = async (jobId) => {
    try {
      await deleteJob(jobId);
      setSuccess('Job stopped');
      fetchJobs();
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
                <InputLabel>Job Type</InputLabel>
                <Select value={jobType} onChange={(e) => setJobType(e.target.value)}>
                  <MenuItem value="analyze_crypto">Analyze Crypto</MenuItem>
                </Select>
              </FormControl>

              <TextField
                fullWidth
                label="Crypto Symbol"
                value={crypto}
                onChange={(e) => setCrypto(e.target.value)}
                placeholder="BTC, ETH, etc."
                sx={{ mb: 2 }}
              />

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
                    justifyContent: 'space-between', 
                    alignItems: 'center',
                    p: 2,
                    border: 1,
                    borderColor: 'divider',
                    borderRadius: 1,
                    mb: 1
                  }}>
                    <Box>
                      <Typography variant="subtitle2">{job.name || job.id}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Next: {job.next_run_time}
                      </Typography>
                    </Box>
                    <IconButton 
                      color="error" 
                      onClick={() => stopJob(job.id)}
                      size="small"
                    >
                      <Stop />
                    </IconButton>
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
