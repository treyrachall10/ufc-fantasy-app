import * as React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import FormLabel from '@mui/material/FormLabel';
import FormControl from '@mui/material/FormControl';
import { useNavigate } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import { useQueryClient } from "@tanstack/react-query";

import ToggleButton, { toggleButtonClasses } from '@mui/material/ToggleButton';
import ToggleButtonGroup, {
  toggleButtonGroupClasses,
} from '@mui/material/ToggleButtonGroup';
import { authFetch } from '../auth/authFetch';

type JoinPayload = {
    join_key: string,
}

export default function JoinLeague(){
    const navigate = useNavigate();
    const queryClient = useQueryClient()

    const [joinKeyError, setJoinKeyError] = React.useState(false)
    const [joinKeyErrorMessage, setJoinKeyErrorMessage] = React.useState('')

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

    // Handles form submission when submit button is clicked
    const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault()

        if (!validateInputs()) {
            return;
        }

        const data = new FormData(event.currentTarget)

        const payload = {
            join_key: data.get('key') as string ,
        }
        createLeagueMutation.mutate(payload)
    }

    // Validates inputs in form
    const validateInputs = () => {
        const key = document.getElementById('key') as HTMLInputElement

        let isValid = true;
        if (key.value.length != 8) {
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
        </Box>
    )

}