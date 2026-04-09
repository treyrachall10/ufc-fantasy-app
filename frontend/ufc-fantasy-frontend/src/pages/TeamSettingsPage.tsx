import { useEffect, useState, type ChangeEvent, type KeyboardEvent } from 'react';
import {
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
import { TeamDataResponse } from '../types/types';

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
    const [confirmOpen, setConfirmOpen] = useState(false);
    const [teamNameError, setTeamNameError] = useState(false);

    const { data, isPending, error } = useQuery<TeamDataResponse>({
        queryKey: ['TeamSettings', params.teamid],
        queryFn: () => authFetch(`http://localhost:8000/team/${params.teamid}`).then((response) => response.json()),
    });

    const changeTeamNameMutation = useMutation({
        mutationFn: async (payload: ChangeTeamNamePayload) => {
            const response = await authFetch(`http://localhost:8000/api/team/${params.teamid}/changeName`, {
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
            setTeamNameError(true);
        },
        onSuccess: (responseData) => {
            const updatedName = responseData?.team?.name || teamName.trim();
            setCurrentTeamName(updatedName);
            setTeamName(updatedName);
            setTeamNameError(false);
        },
    });

    const changeTeamPictureMutation = useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData();
            formData.append('file', file);

            const response = await authFetch(`http://localhost:8000/api/${params.teamid}/changeTeamPicture`, {
                method: 'PATCH',
                body: formData,
            });

            const responseData = await response.json();
            if (!response.ok) {
                throw responseData;
            }

            return responseData;
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
            setTeamNameError(true);
            return;
        }

        setTeamNameError(false);
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
                    <Box
                        sx={{
                            width: '100%',
                            bgcolor: 'dashboardBlack.main',
                            borderRadius: 2,
                            px: 3,
                            py: 2.5,
                        }}
                    >
                        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ width: '100%' }}>
                            <Stack spacing={1.25} sx={{ display: 'flex', alignItems: 'center' }}>
                                <Box
                                    sx={{
                                        width: 120,
                                        height: 120,
                                        borderRadius: '50%',
                                        border: '2px dashed',
                                        borderColor: 'divider',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        color: 'text.secondary',
                                        backgroundColor: 'background.paper',
                                        flexShrink: 0,
                                    }}
                                >
                                    <AddPhotoAlternateOutlinedIcon sx={{ fontSize: 38 }} />
                                </Box>

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

                    <TextField
                        sx={{ width: '100%' }}
                        label="Change Team Name"
                        value={teamName}
                        onChange={(event) => {
                            setTeamName(event.target.value);
                            if (teamNameError) {
                                setTeamNameError(false);
                            }
                        }}
                        onKeyDown={handleTeamNameKeyDown}
                        placeholder="Enter your team name"
                        error={teamNameError}
                    />
                </Stack>
            </Stack>

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
