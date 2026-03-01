import { useEffect } from 'react';
import { Box, Typography } from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuthFetch } from '../auth/authFetch';

type ApiMeResponse = {
	user: {
		id: number;
		email: string;
		username: string;
	};
	profile_complete: boolean;
};

export default function Callback() {
	const authFetch = useAuthFetch();
	const navigate = useNavigate();

	const { data } = useQuery<ApiMeResponse>({
		queryKey: ['me'],
		queryFn: () => authFetch('http://localhost:8000/api/me').then((r) => r.json()),
	});

	useEffect(() => {
		if (data?.profile_complete === false) {
			navigate('/finish-signup');
		} else if (data?.profile_complete === true) {
            navigate('/');
        }
	}, [data, navigate]);

	return (
		<Box
			sx={{
				minHeight: '100dvh',
				bgcolor: 'background.default',
				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',
				flexDirection: 'column',
				gap: 2,
				'@keyframes callbackSpin': {
					'0%': { transform: 'rotate(0deg)' },
					'80%': { transform: 'rotate(1080deg)' },
					'100%': { transform: 'rotate(1080deg)' },
				},
			}}
		>
			<Box
				component="img"
				src='/fist.svg'
				alt="UFC Fantasy"
				sx={{
					width: 90,
					height: 90,
					animation: 'callbackSpin 1.6s cubic-bezier(0.2, 0.7, 0.25, 1) infinite',
				}}
			/>
			<Typography variant="h6" color="text.primary">
				Signing you in
			</Typography>
		</Box>
	);
}
