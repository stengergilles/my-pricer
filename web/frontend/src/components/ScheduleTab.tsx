import React, { useState } from 'react';
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
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';

export const ScheduleTab = () => {
  const { getJobs, scheduleJob, deleteJob, getJobLogs, apiClient } = useApiClient();
  const queryClient = useQueryClient();
  const [expandedJobId, setExpandedJobId] = useState<string | null>(null);
  const [jobLogs, setJobLogs] = useState<string[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  // Form state
  const [jobType, setJobType] = useState('optimize_crypto');
  const [interval, setInterval] = useState(60);
  const [intervalUnit, setIntervalUnit] = useState('seconds');
  const [triggerType, setTriggerType] = useState('interval'); // 'interval' or 'cron'
  const [cronHour, setCronHour] = useState(4); // Default to 4 AM
  const [cronMinute, setCronMinute] = useState(0); // Default to 0 minutes
  const [nTrials, setNTrials] = useState(30); // Default from backend
  const [topCount, setTopCount] = useState(10); // Default from backend
  const [minVolatility, setMinVolatility] = useState(5.0); // Default from backend
  const [maxWorkers, setMaxWorkers] = useState(3); // Default from backend
  const [strategyConfigInput, setStrategyConfigInput] = useState(''); // New state for strategy config JSON
  const [strategyName, setStrategyName] = useState(''); // New state for single strategy selection

  const { data: availableStrategies, isLoading: strategiesLoading } = useQuery<any[]>(
    {
      queryKey: ['availableStrategies'],
      queryFn: () => apiClient.getStrategies(),
      enabled: !!apiClient,
    }
  );

  const { data: jobs = [] } = useQuery({
    queryKey: ['jobs'],
    queryFn: getJobs,
    enabled: !!apiClient,
    refetchInterval: 5000, // Poll every 5 seconds
  });

  const scheduleJobMutation = useMutation({
    mutationFn: scheduleJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  const deleteJobMutation = useMutation({
    mutationFn: deleteJob,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    },
  });

  

  const handleJobClick = async (jobId: string) => {
    if (expandedJobId === jobId) {
      setExpandedJobId(null);
      setJobLogs([]);
    } else {
      setExpandedJobId(jobId);
      setLogsLoading(true);
      try {
        const response = await getJobLogs(jobId);
        setJobLogs(response.logs ? response.logs.split('\n') : []);
      } catch (err) {
        setJobLogs([]);
      } finally {
        setLogsLoading(false);
      }
    }
  };

  const submitJob = async () => {
    let funcKwargs: { [key: string]: any } = {};
    let funcArgs: string[] = [];

    if (jobType === 'optimize_crypto') {
      if (!strategyName) {
        return;
      }
      funcArgs = []; // No crypto argument
      funcKwargs = {
        strategy_name: strategyName,
      };
    } else if (jobType === 'optimize_cryptos_job') {
      funcKwargs = {
        n_trials: nTrials,
        top_count: topCount,
        min_volatility: minVolatility,
        max_workers: maxWorkers,
      };
      if (strategyConfigInput) {
        try {
          const parsedConfig = JSON.parse(strategyConfigInput);
          funcKwargs.strategy_config = parsedConfig;
        } catch (e) {
          return;
        }
      }
    }

    let trigger: string;
    let triggerArgs: { [key: string]: any } = {};

    if (triggerType === 'interval') {
      trigger = 'interval';
      if (intervalUnit === 'seconds') {
        triggerArgs = { seconds: interval };
      } else if (intervalUnit === 'minutes') {
        triggerArgs = { minutes: interval };
      } else if (intervalUnit === 'hours') {
        triggerArgs = { hours: interval };
      } else if (intervalUnit === 'days') {
        triggerArgs = { days: interval };
      }
    } else { // triggerType === 'cron'
      trigger = 'cron';
      triggerArgs = { hour: cronHour, minute: cronMinute };
    }

    scheduleJobMutation.mutate({
      function: jobType,
      trigger: trigger, // Use the dynamically determined trigger
      trigger_args: triggerArgs, // Use the dynamically created triggerArgs
      func_args: funcArgs,
      func_kwargs: funcKwargs,
    });
  };

  const stopJob = async (jobId) => {
    deleteJobMutation.mutate(jobId);
  };

  return (
    <Box sx={{ p: 2 }}>
      {scheduleJobMutation.isError && <Alert severity="error" sx={{ mb: 2 }}>Failed to schedule job: {scheduleJobMutation.error.message}</Alert>}
      {scheduleJobMutation.isSuccess && <Alert severity="success" sx={{ mb: 2 }}>Job scheduled successfully</Alert>}
      {deleteJobMutation.isError && <Alert severity="error" sx={{ mb: 2 }}>Failed to stop job: {deleteJobMutation.error.message}</Alert>}
      {deleteJobMutation.isSuccess && <Alert severity="success" sx={{ mb: 2 }}>Job stopped successfully</Alert>}

      <Grid container spacing={3}>
        {/* Submit Job Form */}
        <Grid item xs={12} md={6}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Schedule New Job</Typography>
              
              <Typography variant="subtitle1" gutterBottom sx={{ mt: 2 }}>Job Parameters</Typography>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel id="job-type-label">Job Type</InputLabel>
                <Select
                  labelId="job-type-label"
                  value={jobType}
                  label="Job Type"
                  onChange={(e) => {
                    setJobType(e.target.value as string);
                  }}
                >
                  <MenuItem value="optimize_crypto">Optimize Single Strategy</MenuItem>
                  <MenuItem value="optimize_cryptos_job">Optimize All Strategies</MenuItem>
                </Select>
              </FormControl>

              {jobType === 'optimize_crypto' && (
                <>
                  <FormControl fullWidth sx={{ mb: 2 }}>
                    <InputLabel id="strategy-label">Strategy</InputLabel>
                    <Select
                      labelId="strategy-label"
                      value={strategyName}
                      label="Strategy"
                      onChange={(e) => setStrategyName(e.target.value as string)}
                    >
                      {strategiesLoading ? (
                        <MenuItem value="">
                          <CircularProgress size={20} />
                          <Typography sx={{ ml: 1 }}>Loading...</Typography>
                        </MenuItem>
                      ) : (
                        availableStrategies?.strategies?.map((s) => (
                          <MenuItem key={s.name} value={s.name}>
                            {s.name}
                          </MenuItem>
                        ))
                      )}
                    </Select>
                  </FormControl>
                </>
              )}

              {jobType === 'optimize_cryptos_job' && (
                <>
                  <TextField
                    fullWidth
                    type="number"
                    label="Number of Trials (n_trials)"
                    value={nTrials}
                    onChange={(e) => setNTrials(Number(e.target.value))}
                    sx={{ mb: 2 }}
                    inputProps={{ min: 1 }}
                  />
                  <TextField
                    fullWidth
                    type="number"
                    label="Top Cryptos to Optimize (top_count)"
                    value={topCount}
                    onChange={(e) => setTopCount(Number(e.target.value))}
                    sx={{ mb: 2 }}
                    inputProps={{ min: 1 }}
                  />
                  <TextField
                    fullWidth
                    type="number"
                    label="Minimum Volatility (min_volatility)"
                    value={minVolatility}
                    onChange={(e) => setMinVolatility(Number(e.target.value))}
                    sx={{ mb: 2 }}
                    inputProps={{ step: 0.1, min: 0 }}
                  />
                  <TextField
                    fullWidth
                    type="number"
                    label="Maximum Workers (max_workers)"
                    value={maxWorkers}
                    onChange={(e) => setMaxWorkers(Number(e.target.value))}
                    sx={{ mb: 2 }}
                    inputProps={{ min: 1 }}
                  />
                  <TextField
                    fullWidth
                    label="Strategy Configuration (JSON)"
                    multiline
                    rows={4}
                    value={strategyConfigInput}
                    onChange={(e) => setStrategyConfigInput(e.target.value)}
                    sx={{ mb: 2 }}
                    placeholder='{"strategy_name_1": {"param1": "value1"}, "strategy_name_2": {"param2": "value2"}}'
                  />
                </>
              )}

              <Typography variant="subtitle1" gutterBottom sx={{ mt: 3 }}>Schedule Parameters</Typography>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel id="trigger-type-label">Schedule Type</InputLabel>
                <Select
                  labelId="trigger-type-label"
                  value={triggerType}
                  label="Schedule Type"
                  onChange={(e) => setTriggerType(e.target.value as string)}
                >
                  <MenuItem value="interval">Interval (e.g., every 5 minutes)</MenuItem>
                  <MenuItem value="cron">Specific Time (e.g., daily at 04:00 AM)</MenuItem>
                </Select>
              </FormControl>

              {triggerType === 'interval' && (
                <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Grid item xs={8}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Interval"
                      value={interval}
                      onChange={(e) => setInterval(Number(e.target.value))}
                      inputProps={{ min: 1 }}
                    />
                  </Grid>
                  <Grid item xs={4}>
                    <FormControl fullWidth>
                      <InputLabel id="interval-unit-label">Unit</InputLabel>
                      <Select
                        labelId="interval-unit-label"
                        value={intervalUnit}
                        label="Unit"
                        onChange={(e) => setIntervalUnit(e.target.value as string)}
                      >
                        <MenuItem value="seconds">Seconds</MenuItem>
                        <MenuItem value="minutes">Minutes</MenuItem>
                        <MenuItem value="hours">Hours</MenuItem>
                        <MenuItem value="days">Days</MenuItem>
                      </Select>
                    </FormControl>
                  </Grid>
                </Grid>
              )}

              {triggerType === 'cron' && (
                <Grid container spacing={2} alignItems="center" sx={{ mb: 2 }}>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Hour (0-23)"
                      value={cronHour}
                      onChange={(e) => setCronHour(Number(e.target.value))}
                      inputProps={{ min: 0, max: 23 }}
                    />
                  </Grid>
                  <Grid item xs={6}>
                    <TextField
                      fullWidth
                      type="number"
                      label="Minute (0-59)"
                      value={cronMinute}
                      onChange={(e) => setCronMinute(Number(e.target.value))}
                      inputProps={{ min: 0, max: 59 }}
                    />
                  </Grid>
                </Grid>
              )}

              <Button
                variant="contained"
                onClick={submitJob}
                disabled={scheduleJobMutation.isPending}
                fullWidth
              >
                {scheduleJobMutation.isPending ? 'Scheduling...' : 'Schedule Job'}
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
                        <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                          Status: {job.status} {job.message && `(${job.message})`}
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