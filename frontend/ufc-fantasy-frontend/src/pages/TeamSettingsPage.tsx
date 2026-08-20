import { useEffect, useState, type ChangeEvent, type KeyboardEvent } from 'react';
import {
    Avatar,
    Box,
    Button,
    Stack,
    TextField,
    Typography,
} from '@mui/material';
import AddPhotoAlternateOutlinedIcon from '@mui/icons-material/AddPhotoAlternateOutlined';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery } from '@tanstack/react-query';
import ListPageLayout from '../components/layout/ListPageLayout';
import { useAuthFetch } from '../auth/authFetch';
import { useCurrentUser } from '../auth/useCurrentUser';
import InfoConfirmDialog from '../components/ui/InfoConfirmDialog';
import SuccessSnackbar from '../components/ui/SuccessSnackbar';
import { TeamDataResponse } from '../types/types';
import { getApiBaseUrl } from '../config/api';

type ChangeTeamNamePayload = {
    name: string;
};

export default function TeamSettingsPage() {
    const params = useParams();
    const authFetch = useAuthFetch();
    const { data: currentUser, isPending: isCurrentUserPending, error: currentUserError } = useCurrentUser();
    const [currentTeamName, setCurrentTeamName] = useState('');
    const [teamName, setTeamName] = useState('');
    const [teamPhotoFile, setTeamPhotoFile] = useState<File | null>(null);
    const [teamPhotoError, setTeamPhotoError] = useState('');
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [teamNameError, setTeamNameError] = useState('');
    const [successMessage, setSuccessMessage] = useState('');
    const [successSnackbarOpen, setSuccessSnackbarOpen] = useState(false);
    const [successSnackbarKey, setSuccessSnackbarKey] = useState(0);

    const { data, isPending, error } = useQuery<TeamDataResponse>({
        queryKey: ['TeamSettings', params.teamid],
        queryFn: () => authFetch(`${getApiBaseUrl()}/team/${params.teamid}`).then((response) => response.json()),
    });

    const changeTeamNameMutation = useMutation({
        mutationFn: async (payload: ChangeTeamNamePayload) => {
            const response = await authFetch(`${getApiBaseUrl()}/api/team/${params.teamid}/changeName`, {
                method: 'POST',
                body: JSON.stringify(payload),
            });

            const responseData = await response.json();
            if (!response.ok) {
                throw responseData;
            }

            return responseData;
        },
        onError: (mutationError: any) => {
            setTeamNameError(mutationError?.detail || 'Unable to change team name.');
        },
        onSuccess: (responseData) => {
            const updatedName = responseData?.team?.name || teamName.trim();
            setCurrentTeamName(updatedName);
            setTeamName(updatedName);
            setTeamNameError('');
            setSuccessMessage(responseData?.detail || '');
            setSuccessSnackbarKey((currentKey) => currentKey + 1);
            setSuccessSnackbarOpen(true);
        },
    });

    const changeTeamPictureMutation = useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData();
            formData.append('image', file);

            const response = await authFetch(`${getApiBaseUrl()}/api/${params.teamid}/SetTeamImage`, {
                method: 'PATCH',
                body: formData,
            });

            const responseData = await response.json();
            if (!response.ok) {
                throw responseData;
            }

            return responseData;
        },
        onError: (mutationError: any) => {
            setTeamPhotoError(mutationError?.detail || 'Unable to change team photo.');
        },
        onSuccess: (responseData) => {
            setTeamPhotoError('');
            setSuccessMessage(responseData?.detail || '');
            setSuccessSnackbarKey((currentKey) => currentKey + 1);
            setSuccessSnackbarOpen(true);
        },
    });

    useEffect(() => {
        if (data?.team.name) {
            setCurrentTeamName(data.team.name);
            setTeamName(data.team.name);
        }
    }, [data?.team.name]);

    const handleOpenConfirm = () => {
        const trimmedTeamName = teamName.trim();
        if (!trimmedTeamName) {
            setTeamNameError('Team name is required.');
            return;
        }

        setTeamNameError('');
        setConfirmOpen(true);
    };

    const handleConfirmChangeTeamName = () => {
        setConfirmOpen(false);
        changeTeamNameMutation.mutate({ name: teamName.trim() });
    };

    const handleTeamNameKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
            event.preventDefault();
            handleOpenConfirm();
        }
    };

    const handleChangeTeamPhoto = (event: ChangeEvent<HTMLInputElement>) => {
        if (!event.target.files?.length) {
            setTeamPhotoFile(null);
            return;
        }

        const selectedFile = event.target.files[0];
        setTeamPhotoFile(selectedFile);
        setTeamPhotoError('');
        changeTeamPictureMutation.mutate(selectedFile);
    };

    if (isPending || isCurrentUserPending) return <span>Loading...</span>;
    if (error || currentUserError) return <span>Oops!</span>;

    const isOwnerViewingTeam = currentUser?.user.username === data.team.owner;

    if (!isOwnerViewingTeam) {
        return (
            <ListPageLayout>
                <Typography variant="h4" color="text.primary">
                    You can only edit your own team settings.
                </Typography>
            </ListPageLayout>
        );
    }

    return (
        <ListPageLayout>
            <Stack spacing={4} sx={{ width: '100%', maxWidth: 420, mx: 'auto', alignItems: 'center' }}>
                <Typography variant="h3" color="text.primary" sx={{ width: '100%', textAlign: 'left' }}>
                    Edit Profile
                </Typography>

                <Stack spacing={2.5} sx={{ width: '100%', alignItems: 'center' }}>
                    <Stack spacing={1} sx={{ width: '100%' }}>
                        <Box
                            sx={{
                                width: '100%',
                                bgcolor: 'dashboardBlack.main',
                                borderRadius: 2,
                                px: 3,
                                py: 2.5,
                                border: teamPhotoError ? '1px solid' : 'none',
                                borderColor: teamPhotoError ? 'error.main' : 'transparent',
                            }}
                        >
                            <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ width: '100%' }}>
                                <Stack spacing={1.25} sx={{ display: 'flex', alignItems: 'center' }}>
                                    <Avatar
                                        src={data.team.img_url || undefined}
                                        alt="Team Photo"
                                        sx={{
                                            width: 120,
                                            height: 120,
                                            border: '2px dashed',
                                            borderColor: 'divider',
                                            color: 'text.secondary',
                                            backgroundColor: 'background.paper',
                                            flexShrink: 0,
                                        }}
                                    >
                                        <AddPhotoAlternateOutlinedIcon sx={{ fontSize: 38 }} />
                                    </Avatar>

                                    <Typography variant="subtitle1" color="text.primary" sx={{ fontWeight: 600 }}>
                                        {currentTeamName || 'Unnamed Team'}
                                    </Typography>
                                </Stack>

                                <Box sx={{ display: 'flex', alignItems: 'center' }}>
                                    <Button
                                        variant="contained"
                                        color="brandAlpha50"
                                        component="label"
                                        sx={{
                                            textTransform: 'none',
                                            borderColor: 'brand.light',
                                            '&:hover': {
                                                borderColor: 'brand.main',
                                            },
                                        }}
                                    >
                                        Change Photo
                                        <input
                                            hidden
                                            type="file"
                                            accept="image/*"
                                            onChange={handleChangeTeamPhoto}
                                        />
                                    </Button>
                                </Box>
                            </Stack>
                        </Box>

                        {teamPhotoError && (
                            <Typography variant="body2" color="error.main">
                                {teamPhotoError}
                            </Typography>
                        )}
                    </Stack>

                    <Stack spacing={1} sx={{ width: '100%' }}>
                        <Box
                            sx={{
                                width: '100%',
                                border: teamNameError ? '1px solid' : 'none',
                                borderColor: teamNameError ? 'error.main' : 'transparent',
                                borderRadius: 1,
                                p: teamNameError ? 1 : 0,
                            }}
                        >
                            <TextField
                                sx={{ width: '100%' }}
                                label="Change Team Name"
                                value={teamName}
                                onChange={(event) => {
                                    setTeamName(event.target.value);
                                    if (teamNameError) {
                                        setTeamNameError('');
                                    }
                                }}
                                onKeyDown={handleTeamNameKeyDown}
                                placeholder="Enter your team name"
                                error={Boolean(teamNameError)}
                            />
                        </Box>

                        {teamNameError && (
                            <Typography variant="body2" color="error.main">
                                {teamNameError}
                            </Typography>
                        )}
                    </Stack>
                </Stack>
            </Stack>

            <SuccessSnackbar
                open={successSnackbarOpen}
                message={successMessage}
                snackbarKey={successSnackbarKey}
                onClose={() => setSuccessSnackbarOpen(false)}
            />

            <InfoConfirmDialog
                open={confirmOpen}
                onClose={() => setConfirmOpen(false)}
                title="Confirm team name"
                items={[
                    {
                        title: 'Current Team Name',
                        content: currentTeamName || 'Unnamed Team',
                    },
                    {
                        title: 'New Team Name',
                        content: teamName.trim(),
                    },
                ]}
                onSubmit={handleConfirmChangeTeamName}
                submitLabel="Change Team Name"
                cancelLabel="Cancel"
            />
        </ListPageLayout>
    );
}
