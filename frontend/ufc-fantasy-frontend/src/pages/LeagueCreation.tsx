import * as React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import FormLabel from '@mui/material/FormLabel';
import FormControl from '@mui/material/FormControl';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useQueryClient } from "@tanstack/react-query";

import ToggleButton, { toggleButtonClasses } from '@mui/material/ToggleButton';
import ToggleButtonGroup, {
  toggleButtonGroupClasses,
} from '@mui/material/ToggleButtonGroup';
import { useAuthFetch } from '../auth/authFetch';

type LeaguePayload = {
    leagueName: string,
    teams: number
}

export default function LeagueCreation(){
    const navigate = useNavigate();
    const queryClient = useQueryClient()
    const authFetch = useAuthFetch();

    const [leagueNameError, setLeagueNameError] = React.useState(false)
    const [leagueNameErrorMessage, setLeagueNameErrorMessage] = React.useState('')

    const [teams, setTeams] = React.useState<string | null>(null)
    const [teamError, setTeamError] = React.useState(false)
    const [teamErrorMessage, setTeamErrorMessage] = React.useState('')

    const [confirmDialogOpen, setConfirmDialogOpen] = React.useState(false)
    const [pendingPayload, setPendingPayload] = React.useState<LeaguePayload | null>(null)

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

    // Handles form submission - shows confirmation dialog
    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault()
        console.log(teams)
        if (!validateInputs()) {
            return;
        }

        const data = new FormData(event.currentTarget)

        const payload = {
            leagueName: data.get('league') as string ,
            teams: Number(teams),
        }
        // Store payload and open dialog instead of immediately submitting
        setPendingPayload(payload)
        setConfirmDialogOpen(true)
    }

    // Handles confirmation - actually creates the league
    const handleConfirmCreate = () => {
        if (pendingPayload) {
            createLeagueMutation.mutate(pendingPayload)
            setConfirmDialogOpen(false)
            setPendingPayload(null)
        }
    }

    // Handles cancellation - closes dialog without creating
    const handleCancelCreate = () => {
        setConfirmDialogOpen(false)
        setPendingPayload(null)
    }

    // Handles team selection
    const handleChange = (event: React.MouseEvent<HTMLElement>, value: string | null) => {
        console.log(value)
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
                alignItems: 'flex-start',
                pt: { xs: 4, md: 8 }
            }}>
            <Box sx={{
                display: 'flex',
                flexDirection: 'column',
                width: { xs: '90%', sm: '70%', md: '50%', lg: '45%' },
                gap: 3
            }}>
            <Typography variant='h2' sx={{ mb: 1 }}>Create League</Typography>
            {/* League creation card container*/}
            <Box sx={{
                    bgcolor: 'dashboardBlack.main',
                    width: '100%',
                    display: 'flex',
                    justifyContent: 'center',
                    alignItems: 'center',
                    borderRadius: 3,
                    border: '1px solid',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
                    backdropFilter: 'blur(10px)'
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
                            padding: { xs: 3, md: 4 },
                            gap: 3,
                            }}
                        >
                            <FormControl fullWidth>
                                <FormLabel htmlFor='leagueName' sx={{
                                    color: 'white',
                                    fontSize: '1rem',
                                    fontWeight: 600,
                                    mb: 1.5,
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.05em'
                                }}>
                                    League Name
                                </FormLabel>
                                <TextField
                                    error={leagueNameError}
                                    helperText={leagueNameErrorMessage}
                                    id="league"
                                    type="text"
                                    name="league"
                                    placeholder="Real Fight Fans League"
                                    autoComplete="off"
                                    autoFocus
                                    required
                                    fullWidth
                                    variant="outlined"
                                    color={leagueNameError ? 'error' : 'primary'}
                                    sx={{
                                        '& .MuiOutlinedInput-root': {
                                            color: 'white',
                                            fontSize: '1rem'
                                        }
                                    }}
                                />
                          </FormControl>
                          <FormControl fullWidth> 
                            <FormLabel htmlFor='teamSelect' sx={{
                                color: 'white',
                                fontSize: '1rem',
                                fontWeight: 600,
                                mb: 2,
                                textTransform: 'uppercase',
                                letterSpacing: '0.05em',
                                textAlign: 'center'
                            }}>
                                Number of Teams
                            </FormLabel>     
                                <ToggleButtonGroup
                                    exclusive
                                    value={teams}
                                    color='primary'
                                    onChange={handleChange}
                                    sx={{
                                        display: 'flex',
                                        justifyContent: 'center',
                                        flexWrap: 'wrap'
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
                                            border: '2px solid rgba(255, 255, 255, 0.2)',
                                            '&.Mui-selected': {
                                                backgroundColor: 'brand.light',
                                                borderColor: 'brand.light',
                                                color: 'white',
                                            },
                                            '&:hover': {
                                                borderColor: 'brand.light',
                                            }
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
                                        sx={{ mt: 1, textAlign: 'center', fontWeight: 500 }}
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
                            alignSelf: 'center',
                            borderRadius: '8px',
                            border: '1px solid',
                            borderColor: 'brand.light',
                            '&:hover': {
                                borderColor: 'brand.main',
                            }                        
                        }}
                        >
                        Create League
                    </Button>
                    </Box>
            </Box>
            </Box>

            {/* Confirmation Dialog */}
            <Dialog
                open={confirmDialogOpen}
                onClose={handleCancelCreate}
                maxWidth="sm"
                fullWidth
            >
                <DialogTitle sx={{ 
                    fontWeight: 700,
                    fontSize: '1.3rem',
                    textAlign: 'center',
                    pb: 1
                }}>
                    Ready to Build Your League?
                </DialogTitle>
                <DialogContent sx={{ pt: 2 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <Box sx={{ p: 2, bgcolor: 'rgba(255, 255, 255, 0.05)', borderRadius: 1.5 }}>
                            <Typography sx={{ fontSize: '0.875rem', color: 'text.secondary', mb: 0.5, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                                League Name
                            </Typography>
                            <Typography sx={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                {pendingPayload?.leagueName}
                            </Typography>
                        </Box>
                        <Box sx={{ p: 2, bgcolor: 'rgba(255, 255, 255, 0.05)', borderRadius: 1.5 }}>
                            <Typography sx={{ fontSize: '0.875rem', color: 'text.secondary', mb: 0.5, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
                                Number of Teams
                            </Typography>
                            <Typography sx={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                {pendingPayload?.teams} Teams
                            </Typography>
                        </Box>
                    </Box>
                    <Typography sx={{ mt: 3, color: 'text.secondary', fontSize: '0.95rem', textAlign: 'center', fontStyle: 'italic' }}>
                        You can invite other players to join your league after creation.
                    </Typography>
                </DialogContent>
                <DialogActions sx={{ gap: 1, p: 2.5, borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <Button
                        onClick={handleCancelCreate}
                        variant="contained"
                        color="whiteAlpha20"
                        sx={{
                            flex: 1,
                            borderColor: 'gray900.main',
                            '&:hover': {
                                borderColor: 'gray800.main'
                            }
                        }}
                    >
                        Cancel
                    </Button>
                    <Button
                        onClick={handleConfirmCreate}
                        variant="contained"
                        color="brandAlpha50"
                        sx={{
                            flex: 1,
                            borderRadius: '8px',
                            border: '1px solid',
                            borderColor: 'brand.light',
                            '&:hover': {
                                borderColor: 'brand.main',
                            }
                        }}
                    >
                        Create League
                    </Button>
                </DialogActions>
            </Dialog>
        </Box>
    )

}