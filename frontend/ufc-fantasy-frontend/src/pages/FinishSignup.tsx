import { useState } from 'react';
import {
	Box,
	Button,
	Dialog,
	DialogActions,
	DialogContent,
	DialogContentText,
	DialogTitle,
	Stack,
	TextField,
	Typography,
} from '@mui/material';
import { useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuthFetch } from '../auth/authFetch';

type SetUsernamePayload = {
	username: string;
};

export default function FinishSignup() {
	const authFetch = useAuthFetch();
	const navigate = useNavigate();
	const [username, setUsername] = useState('');
	const [confirmOpen, setConfirmOpen] = useState(false);
	const [usernameError, setUsernameError] = useState(false);
	const [usernameErrorMessage, setUsernameErrorMessage] = useState('');

	const setUsernameMutation = useMutation({
		mutationFn: async (payload: SetUsernamePayload) => {
			const response = await authFetch('http://localhost:8000/api/setUserName', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
				},
				body: JSON.stringify(payload),
			});

			const data = await response.json();
			if (!response.ok) {
				throw data;
			}

			return data;
		},
		onError: (error: any) => {
			const message =
				error?.detail ||
				error?.message ||
				(typeof error === 'string' ? error : 'Unable to set username.');
			setUsernameError(true);
			setUsernameErrorMessage(message);
		},
		onSuccess: () => {
			navigate('/');
		},
	});

	const handleSubmit = () => {
		const trimmedUsername = username.trim();
		if (!trimmedUsername) {
			setUsernameError(true);
			setUsernameErrorMessage('Username is required.');
			return;
		}
		if (/\s/.test(trimmedUsername)) {
			setUsernameError(true);
			setUsernameErrorMessage('Username cannot contain spaces.');
			return;
		}

		setUsernameError(false);
		setUsernameErrorMessage('');
		setConfirmOpen(true);
	};

	const handleConfirm = () => {
		setConfirmOpen(false);
		const trimmedUsername = username.trim();
		setUsernameMutation.mutate({ username: trimmedUsername });
	};

	return (
		<Box
			sx={{
				minHeight: '100dvh',
				bgcolor: 'background.default',
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
				px: 2,
			}}
		>
			<Stack
				spacing={2}
				sx={{
					width: '100%',
					maxWidth: 420,
					alignItems: 'center',
				}}
			>
				<Typography variant="h4" color="text.primary">
					Choose a username
				</Typography>
				<TextField
					fullWidth
					id="username"
					label="Username"
					value={username}
					onChange={(event) => setUsername(event.target.value)}
					error={usernameError}
					helperText={usernameError ? usernameErrorMessage : ' '}
				/>
                <Button
                    type="submit"
                    variant="contained"
                    onClick={handleSubmit}
                    color='brandAlpha50' 
                    disabled={setUsernameMutation.isPending}
                    sx={{ 
                        borderColor: 'brand.light',
                        '&:hover': {
                            borderColor: 'brand.main'
                        }                        
                    }}
                >
                    Submit
                </Button>
			</Stack>

			<Dialog open={confirmOpen} onClose={() => setConfirmOpen(false)}>
				<DialogTitle>Confirm username</DialogTitle>
				<DialogContent>
					<DialogContentText>
						Make "{username}" your username?
					</DialogContentText>
				</DialogContent>
				<DialogActions>
					<Button onClick={() => setConfirmOpen(false)}>Cancel</Button>
					<Button
						variant="contained"
						color="brandAlpha50"
						onClick={handleConfirm}
						sx={{ 
                        borderColor: 'brand.light',
                        '&:hover': {
                            borderColor: 'brand.main'
                        }                        
                    }}
					>
						Yes, I am sure
					</Button>
				</DialogActions>
			</Dialog>
		</Box>
	);
}
