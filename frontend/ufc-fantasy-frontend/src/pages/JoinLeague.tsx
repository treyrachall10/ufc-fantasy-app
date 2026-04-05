import * as React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import FormLabel from '@mui/material/FormLabel';
import FormControl from '@mui/material/FormControl';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import { useQueryClient } from "@tanstack/react-query";
import { useAuthFetch } from '../auth/authFetch';
import InfoConfirmDialog from '../components/ui/InfoConfirmDialog';

type JoinPayload = {
    join_key: string,
}

type LeaguePreview = {
    league_name: string,
    creator_username: string,
}

export default function JoinLeague(){
    const navigate = useNavigate();
    const queryClient = useQueryClient()
    const authFetch = useAuthFetch();

    const [joinKeyError, setJoinKeyError] = React.useState(false)
    const [joinKeyErrorMessage, setJoinKeyErrorMessage] = React.useState('')
    const [confirmDialogOpen, setConfirmDialogOpen] = React.useState(false)
    const [pendingJoinPayload, setPendingJoinPayload] = React.useState<JoinPayload | null>(null)
    const [previewJoinKey, setPreviewJoinKey] = React.useState('')
    const [leaguePreview, setLeaguePreview] = React.useState<LeaguePreview | null>(null)
    const [shouldFetchPreview, setShouldFetchPreview] = React.useState(false)

    const previewLeagueQuery = useQuery<LeaguePreview>({
        queryKey: ['previewLeague', previewJoinKey],
        enabled: shouldFetchPreview && previewJoinKey.length === 8,
        retry: false,
        queryFn: async ({ queryKey }) => {
            const [, joinKey] = queryKey as [string, string]
            const response = await authFetch('http://localhost:8000/api/previewLeague', {
                method: 'POST',
                body: JSON.stringify({ join_key: joinKey }),
            })

            const data = await response.json()

            if (!response.ok) {
                throw { ...data, status: response.status }
            }

            return data as LeaguePreview
        },
    })

    React.useEffect(() => {
        if (previewLeagueQuery.data) {
            setLeaguePreview(previewLeagueQuery.data)
            setConfirmDialogOpen(true)
            setShouldFetchPreview(false)
        }
    }, [previewLeagueQuery.data])

    React.useEffect(() => {
        if (previewLeagueQuery.error) {
            const error = previewLeagueQuery.error as any
            setJoinKeyError(true)
            if (error?.status === 404) {
                setJoinKeyErrorMessage('There is no league with this key')
            } else {
                setJoinKeyErrorMessage(error?.detail ?? 'Unable to find league.')
            }
            setShouldFetchPreview(false)
        }
    }, [previewLeagueQuery.error])

    // POST request to login a user
      const createLeagueMutation = useMutation({
        mutationFn: async (payload: JoinPayload) => {
          const response = await authFetch('http://localhost:8000/league/join', {
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
            setJoinKeyError(true);
            setJoinKeyErrorMessage(error.detail);        
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
            navigate(`/league/${data.league_id}`);
        }
      })

    // Handles form submission - validates key and fetches league preview
    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault()

        if (!validateInputs()) {
            return;
        }

        const data = new FormData(event.currentTarget)

        const payload = {
            join_key: data.get('key') as string ,
        }

        setPendingJoinPayload(payload)
        setPreviewJoinKey(payload.join_key)
        setShouldFetchPreview(true)
    }

    const handleConfirmJoin = () => {
        if (pendingJoinPayload) {
            createLeagueMutation.mutate(pendingJoinPayload)
            setConfirmDialogOpen(false)
            setPendingJoinPayload(null)
            setLeaguePreview(null)
        }
    }

    const handleCancelJoin = () => {
        setConfirmDialogOpen(false)
        setPendingJoinPayload(null)
        setLeaguePreview(null)
    }

    // Validates inputs in form
    const validateInputs = () => {
        const key = document.getElementById('key') as HTMLInputElement

        let isValid = true;
        if (key.value.length !== 8) {
            setJoinKeyError(true);
            setJoinKeyErrorMessage('Join key must be exactly 8 characters.');
            isValid = false;
        } else {
            setJoinKeyError(false);
            setJoinKeyErrorMessage('');
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
                pt: 6
            }}>
            <Box sx={{
                display: 'flex',
                flexDirection: 'column',
                width: '50%',
                gap: 2
            }}>
            <Typography variant='h2'>Join a League</Typography>
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
                                <FormLabel htmlFor='joinKey' sx={{color: 'white', fontSize: '1.3rem'}}>Join Key</FormLabel>
                                <TextField
                                error={joinKeyError}
                                helperText={joinKeyErrorMessage}
                                id="key"
                                type="key"
                                name="key"
                                placeholder="League key (e.g. ABC123XY)"
                                autoComplete="email"
                                autoFocus
                                required
                                fullWidth
                                variant="outlined"
                                color={joinKeyError ? 'error' : 'primary'}
                                />
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

            <InfoConfirmDialog
                open={confirmDialogOpen}
                onClose={handleCancelJoin}
                title="Confirm League Join"
                items={[
                    { title: 'Join Key', content: pendingJoinPayload?.join_key ?? '' },
                    { title: 'League Name', content: leaguePreview?.league_name ?? '' },
                    { title: 'League Owner', content: leaguePreview?.creator_username ?? '' },
                ]}
                onSubmit={handleConfirmJoin}
                submitLabel="Join League"
                cancelLabel="Cancel"
            />
        </Box>
    )

}