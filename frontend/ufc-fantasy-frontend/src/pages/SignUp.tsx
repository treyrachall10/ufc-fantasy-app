import * as React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import FormControlLabel from '@mui/material/FormControlLabel';
import Divider from '@mui/material/Divider';
import FormLabel from '@mui/material/FormLabel';
import FormControl from '@mui/material/FormControl';
import Link from '@mui/material/Link';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import MuiCard from '@mui/material/Card';
import { styled } from '@mui/material/styles';
import { GoogleIcon } from '../components/CustomIcons';
import fistLogo from '../images/fist-svgrepo-com.svg';

// Tanstack imports
import { useMutation } from '@tanstack/react-query';

type CreateUserPayload = {
  username: string | null
  email: string | null
  password: string | null
}

const Card = styled(MuiCard)(({ theme }) => ({
  display: 'flex',
  flexDirection: 'column',
  alignSelf: 'center',
  width: '100%',
  padding: theme.spacing(4),
  gap: theme.spacing(2),
  margin: 'auto',
  maxWidth: '450px',
  boxShadow:
    'hsla(220, 30%, 5%, 0.05) 0px 5px 15px 0px, hsla(220, 25%, 10%, 0.05) 0px 15px 35px -5px',
  ...theme.applyStyles('dark', {
    boxShadow:
      'hsla(220, 30%, 5%, 0.5) 0px 5px 15px 0px, hsla(220, 25%, 10%, 0.08) 0px 15px 35px -5px',
  }),
}));

export default function SignUp() {

  // POST request to create a user
  const createUserMutation = useMutation({
    mutationFn: (payload: CreateUserPayload ) => {
      return fetch('http://localhost:8000/auth/signup/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
    },
  })
    
  const [emailError, setEmailError] = React.useState(false);
  const [passwordError, setPasswordError] = React.useState(false);
  const [nameError, setNameError] = React.useState(false);

  const [emailErrorMessage, setEmailErrorMessage] = React.useState('');
  const [passwordErrorMessage, setPasswordErrorMessage] = React.useState('');
  const [nameErrorMessage, setNameErrorMessage] = React.useState('');

  const validateInputs = () => {
    const email = document.getElementById('email') as HTMLInputElement;
    const password = document.getElementById('password') as HTMLInputElement;
    const name = document.getElementById('username') as HTMLInputElement;

    let valid = true;

    if (!name.value) {
      setNameError(true);
      setNameErrorMessage('Display name is required.');
      valid = false;
    } else {
      setNameError(false);
      setNameErrorMessage('');
    }

    if (!email.value || !/\S+@\S+\.\S+/.test(email.value)) {
      setEmailError(true);
      setEmailErrorMessage('Please enter a valid email.');
      valid = false;
    } else {
      setEmailError(false);
      setEmailErrorMessage('');
    }

    if (!password.value || password.value.length < 8) {
      setPasswordError(true);
      setPasswordErrorMessage('Password must be at least 8 characters.');
      valid = false;
    } else {
      setPasswordError(false);
      setPasswordErrorMessage('');
    }

    return valid;
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!validateInputs()) {
      return;
    }

    const data = new FormData(event.currentTarget);
    const payload = {
      username: data.get('username') as string,
      email: data.get('email') as string,
      password: data.get('password') as string,
    }

    createUserMutation.mutate(payload)
  };

  return (
    <Box
      sx={{
        background: 'radial-gradient(hsla(0, 91%, 43%, 0.5), hsla(0, 91%, 43%, 0.05))',
        minHeight: '100vh',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <Card
        variant="outlined"
        sx={{
          bgcolor: 'hsla(5, 7%, 10%, 0.4)',
          borderColor: 'gray900.main',
          borderRadius: 4,
        }}
      >
        <img src={fistLogo} alt="Home" style={{ height: 42 }} />

        <Typography component="h1" variant="h4">
          Sign up
        </Typography>

        <Box
          component="form"
          onSubmit={handleSubmit}
          sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}
        >
          <FormControl>
            <FormLabel htmlFor="name">Username</FormLabel>
            <TextField
              id="username"
              name="username"
              placeholder="DoBronxFan"
              required
              error={nameError}
              helperText={nameErrorMessage}
              fullWidth
            />
          </FormControl>

          <FormControl>
            <FormLabel htmlFor="email">Email</FormLabel>
            <TextField
              id="email"
              name="email"
              placeholder="your@email.com"
              required
              error={emailError}
              helperText={emailErrorMessage}
              fullWidth
            />
          </FormControl>

          <FormControl>
            <FormLabel htmlFor="password">Password</FormLabel>
            <TextField
              id="password"
              name="password"
              type="password"
              placeholder="••••••"
              required
              error={passwordError}
              helperText={passwordErrorMessage}
              fullWidth
            />
          </FormControl>

          <FormControlLabel
            control={
              <Checkbox
                sx={{
                  color: 'hsla(0, 0%, 60%, 0.6)',
                  '&.Mui-checked': { color: 'hsla(0, 91%, 43%, 1)' },
                }}
              />
            }
            label="I want to receive updates via email."
          />

          <Button
            type="submit"
            variant="contained"
            color="brandAlpha50"
            sx={{
              borderColor: 'brand.light',
              '&:hover': { borderColor: 'brand.main' },
            }}
          >
            Create account
          </Button>
        </Box>

        <Divider>or</Divider>

        <Button
          variant="outlined"
          color="whiteAlpha20"
          startIcon={<GoogleIcon />}
          sx={{
            borderColor: 'gray900.main',
            '&:hover': { borderColor: 'gray800.main' },
          }}
        >
          Sign up with Google
        </Button>

        <Typography sx={{ textAlign: 'center' }}>
          Already have an account?{' '}
          <Link href="/sign-in" variant="body2">
            Sign in
          </Link>
        </Typography>
      </Card>
    </Box>
  );
}
