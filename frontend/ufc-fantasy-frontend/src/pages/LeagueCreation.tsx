import * as React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import MuiCard from '@mui/material/Card';
import FormLabel from '@mui/material/FormLabel';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import { useContext } from 'react';
import { AuthContext } from '../auth/AuthProvider';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useQueryClient } from "@tanstack/react-query";

import ToggleButton, { toggleButtonClasses } from '@mui/material/ToggleButton';
import ToggleButtonGroup, {
  toggleButtonGroupClasses,
} from '@mui/material/ToggleButtonGroup';
import { styled } from '@mui/material/styles';
import { authFetch } from '../auth/authFetch';

type LeaguePayload = {
    leagueName: string,
    teams: number
}

export default function LeagueCreation(){
    const navigate = useNavigate();
    const queryClient = useQueryClient()

    const [leagueNameError, setLeagueNameError] = React.useState(false)
    const [leagueNameErrorMessage, setLeagueNameErrorMessage] = React.useState('')

    const [teams, setTeams] = React.useState<string | null>(null)
    const [teamError, setTeamError] = React.useState(false)
    const [teamErrorMessage, setTeamErrorMessage] = React.useState('')

    // POST request to login a user
      const createLeagueMutation = useMutation({
        mutationFn: async (payload: LeaguePayload) => {
          const response = await authFetch('http://localhost:8000/create-league', {
            method: 'POST',
            body: JSON.stringify(payload),
          })
    
          const data = await response.json()
    
          if (!response.ok) {
            throw data
          }
    
          return data
        },
    
        // Do something if fails
        onError: (error: any) => {
          if (error){
            setLeagueNameError(true);
            setLeagueNameErrorMessage(error.detail);        
            setTeamError(true);
            setTeamErrorMessage(error.detail);
          }
        },
    
        onSuccess: (data) => {
            queryClient.setQueryData(["league", data.league_id],
                {
                    id: data.league_id,
                    join_key: data.join_key,
                    draft_id: data.draft_id,
                    draft_status: data.draft_status,
                    member: data.member
                }
            )
            queryClient.setQueryData(["team", data.team.id],
                data.team
            )
            navigate('/leagues');
        }
      })

    // Handles form submission when submit button is clicked
    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault()

        if (!validateInputs()) {
            return;
        }

        const data = new FormData(event.currentTarget)

        const payload = {
            leagueName: data.get('league') as string ,
            teams: Number(data.get('teams')),
        }
        createLeagueMutation.mutate(payload)
    }

    // Handles team selection
    const handleChange = (event: React.MouseEvent<HTMLElement>, value: string | null) => {
        if (value !== null) {
            setTeams(value);
        }
    }

    // Validates inputs in form
    const validateInputs = () => {
        const league = document.getElementById('league') as HTMLInputElement

        let isValid = true;
        if (league.value.length > 64) {
            setLeagueNameError(true);
            setLeagueNameErrorMessage('Name must be less than 64 characters.');
            isValid = false;
        } else {
            setLeagueNameError(false);
            setLeagueNameErrorMessage('');
        }

        if (teams === null) {
            setTeamError(true);
            setTeamErrorMessage('Must choose number of teams in league.');
            isValid = false;
        } else {
            setTeamError(false);
            setTeamErrorMessage('');
        }
        return isValid;
    }
    
    return (
        //Background
        <Box sx={{
                height: '100%',
                width: '100%',
                display: 'flex',
                justifyContent: 'center',
            }}>
            <Box sx={{
                display: 'flex',
                flexDirection: 'column',
                width: '50%',
                gap: 2
            }}>
            <Typography variant='h2'>Create League</Typography>
            {/* League creation card container*/}
            <Box sx={{
                    bgcolor: 'dashboardBlack.main',
                    width: '100%',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    borderRadius: 2,
                }}>
                    {/* Form */}
                    <Box
                        component='form'
                        onSubmit={handleSubmit}
                        noValidate
                        sx={{
                            display: 'flex',
                            flexDirection: 'column',
                            width: '100%',
                            padding: 2,
                            gap: 2,
                            }}
                        >
                            <FormControl>
                                <FormLabel htmlFor='leagueName' sx={{color: 'white', fontSize: '1.3rem'}}>League Name</FormLabel>
                                <TextField
                                error={leagueNameError}
                                helperText={leagueNameErrorMessage}
                                id="league"
                                type="league"
                                name="league"
                                placeholder="Real Fight Fans League"
                                autoComplete="email"
                                autoFocus
                                required
                                fullWidth
                                variant="outlined"
                                color={leagueNameError ? 'error' : 'primary'}
                                />
                          </FormControl>
                          <FormControl> 
                            <FormLabel htmlFor='leagueName' sx={{color: 'white', alignSelf: 'center', fontSize: '1.3rem'}}>Number of Teams</FormLabel>     
                                <ToggleButtonGroup
                                    exclusive
                                    value={teams}
                                    color='primary'
                                    onChange={handleChange}
                                    sx={{
                                        display: 'flex',
                                        justifyContent: 'center',
                                        gap: 2, 
                                    }}
                                    >
                                    {['4','6','8','10'].map(v => (
                                        <ToggleButton
                                        key={v}
                                        value={v}
                                        sx={{
                                            width: 56,
                                            height: 56,
                                            p: 0,
                                            fontSize: '1rem',
                                            color: 'white',
                                        }}
                                        >
                                        {v}
                                        </ToggleButton>
                                    ))}
                                    </ToggleButtonGroup>
                                      {teamError && (
                                        <Typography
                                        variant="caption"
                                        color="error"
                                        sx={{ mt: 1, textAlign: 'center' }}
                                        >
                                        {teamErrorMessage}
                                        </Typography>
                                    )}
                            </FormControl>
                    <Button
                        type='submit'
                        variant="contained" 
                        color='brandAlpha50'
                        sx={{ 
                            borderColor: 'brand.light',
                            alignSelf: 'center',
                            '&:hover': {
                                borderColor: 'brand.main'
                            }                        
                        }}
                        >
                        Submit
                    </Button>
                    </Box>
            </Box>
            </Box>
        </Box>
    )

}