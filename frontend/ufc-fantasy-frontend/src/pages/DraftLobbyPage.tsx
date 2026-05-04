import { Box, Grid, Paper, Stack, Typography, FormControl, Select, MenuItem, Avatar, Button, Dialog, DialogTitle, DialogContent, DialogActions, useMediaQuery, TextField } from '@mui/material';
import IconButton from '@mui/material/IconButton';
import InputAdornment from '@mui/material/InputAdornment';
import SearchIcon from '@mui/icons-material/Search';
import ListPageLayout from '../components/layout/ListPageLayout';
import DraftPlayerCard from '../components/Draftcards/DraftPlayerCard';
import { KeyboardEvent, useEffect, useState } from 'react';
import AnimatedList from '../components/Animations/AnimatedList';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useMutation } from '@tanstack/react-query';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthFetch } from '../auth/authFetch';
import { supabase } from '../supabase';
import { useNavigate, useParams } from 'react-router-dom';
import { DataGrid, GridColDef, GridPaginationModel, GridRenderCellParams } from '@mui/x-data-grid';
import { LeagueInfo, TeamDataResponse, DraftHistoryItem, DraftOrderTeam, PaginatedResponse } from '../types/types';

// Payload type for drafting a fighter
interface DraftFighterPayload {
    team_id: number;
    fighter_id: number;
}

interface PendingDraftPick {
    fighter_id: number;
    fighter_name: string;
    weight_class: string;
}

// Weight class text to numeric mapping
const WEIGHT_CLASS_MAP: Record<string, number> = {
    'HW': 265,
    'LHW': 205,
    'MW': 185,
    'WW': 170,
    'LW': 155,
    'FW': 145,
    'BW': 135,
    'FLW': 125,
    'SW': 115,
};

// TypeScript interface for draft state
interface DraftState {
    draft_status: string;
    current_pick: number;
    pick_start_time: string;
    team_to_pick_id: number;
    user_team_id: number;
}

// TypeScript interface for draftable fighters
interface DraftableFighter {
    fighter: {
        fighter_id: number;
        full_name: string;
        weight: number;
        slot_type: string;
    };
    fantasy: {
        last_fight_points: number;
        average_points: number;
    };
}

export default function DraftLobbyPage() {
    const params = useParams<{ leagueId: string; draftId: string }>();
    const navigate = useNavigate();
    const isMobile = useMediaQuery('(max-width: 600px)');
    const queryClient = useQueryClient();
    const authFetch = useAuthFetch();
    const [paginationModel, setPaginationModel] = useState<GridPaginationModel>({ page: 0, pageSize: 25 });
    const { page, pageSize } = paginationModel;
    const [typedSearch, setTypedSearch] = useState('');
    const [submittedSearch, setSubmittedSearch] = useState('');
    const [selectedTeamId, setSelectedTeamId] = useState<number | undefined>();
    const [rosterDialogOpen, setRosterDialogOpen] = useState(false);
    const [flexDialogOpen, setFlexDialogOpen] = useState(false);
    const [pendingFlexFighterId, setPendingFlexFighterId] = useState<number | null>(null);
    const [confirmDraftDialogOpen, setConfirmDraftDialogOpen] = useState(false);
    const [pendingDraftPick, setPendingDraftPick] = useState<PendingDraftPick | null>(null);
    
    // State for weight class filter - holds the selected weight class text value
    const [selectedWeightClass, setSelectedWeightClass] = useState('');
    // State for numeric weight class translated from the text filter
    const [selectedNumericWeightClass, setSelectedNumericWeightClass] = useState<number | null>(null);
    
    // Effect to translate weight class text to numeric value when filter changes
    useEffect(() => {
        if (selectedWeightClass === '') {
            setSelectedNumericWeightClass(null);
        } else {
            const numericValue = WEIGHT_CLASS_MAP[selectedWeightClass];
            setSelectedNumericWeightClass(numericValue || null);
        }
    }, [selectedWeightClass]);

    useEffect(() => {
        setPaginationModel((prev) => ({ ...prev, page: 0 }));
    }, [selectedWeightClass, submittedSearch]);

    const handleSearchSubmit = () => {
        setSubmittedSearch(typedSearch.trim());
    };

    const handleSearchKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
        if (event.key === 'Enter') {
            handleSearchSubmit();
        }
    };
    
    // Draft Button Renderer for DataGrid - Calls the handleDraftPick function with the fighter's ID when clicked.
    const DraftButton = (params: GridRenderCellParams) => {
        return (
            <Button
                variant="contained"
                color="brandAlpha50"
                disabled={!canDraft}
                onClick={() =>
                    handleDraftPick({
                        fighterId: Number(params.id),
                        fighterName: String(params.row.fighter),
                        weightClass: String(params.row.weightClass),
                    })
                }
                size={isMobile ? 'small' : undefined}
                sx={{
                    textWrap: 'nowrap',
                    borderColor: 'brand.light',
                    '&:hover': { borderColor: 'brand.main' },
                    ...(isMobile && {
                        padding: '4px 10px',
                        fontSize: '0.7rem',
                        fontWeight: 400,
                    }),
                }}
            >
                Draft
            </Button>
        )
    }
    // Fetch Draft State Data in rolling intervals using refetchinterval to keep the timer, current pick, and status updated in real-time
    const { data: draftStateData } = useQuery<DraftState>({
        queryKey: ['draft', params.draftId, 'state'],
        queryFn: () => authFetch(`http://localhost:8000/draft/${params.draftId}/state`).then(r => r.json()),
    })

    // WEBSOCKET
    useEffect(() => {
        const channel = supabase
            .channel('draft-lobby-changes')
            .on(
                'postgres_changes',
                {
                    event: '*',   // Listen to all events (INSERT, UPDATE, DELETE)
                    schema: 'public'
                },
                (payload) => {
                    //  fires the exact millisecond the database changes
                    console.log('Database event detected! Fetching fresh data...', payload);
                    // Invalidate all queries SIMULTANEOUSLY so they fetch in parallel
                    queryClient.invalidateQueries({ queryKey: ['draft', params.draftId, 'state'] });
                    queryClient.invalidateQueries({ queryKey: ['draft', params.draftId, 'pastPicks'] });
                    queryClient.invalidateQueries({ queryKey: ['team', selectedTeamId] });
                    queryClient.invalidateQueries({ queryKey: ['draft', params.draftId, 'draftableFighters'] });
                }
            )
            .subscribe();
        return () => { //close the WebSocket
            supabase.removeChannel(channel);
        };
    }, [params.draftId, queryClient]);   // Tell React to rerun hook only if the draftId changes

    useEffect(() => {
        if (!draftStateData) return;

        if (draftStateData.draft_status === 'COMPLETED') {
            if (draftStateData.user_team_id) {
                navigate(`/team/${draftStateData.user_team_id}`);
                return;
            }

            if (params.leagueId) {
                navigate(`/league/${params.leagueId}`);
            }

            return;
        }

        if (draftStateData.draft_status !== 'IN_PROGRESS' && params.leagueId) {
            navigate(`/league/${params.leagueId}`);
        }
    }, [draftStateData, navigate, params.leagueId]);

    // Fetch Draftable Fighters for Draft Board
    const { data: draftableFightersData, isPending: isDraftableFightersPending } = useQuery<PaginatedResponse<DraftableFighter>>({
        queryKey: ['draft', params.draftId, 'draftableFighters', page, pageSize, selectedNumericWeightClass, submittedSearch],
        queryFn: () => {
            const queryParams = new URLSearchParams({
                page: String(page + 1),
                page_size: String(pageSize),
            });

            // Add weight class filter to API request if one is selected
            if (selectedNumericWeightClass) {
                queryParams.set('weight', selectedNumericWeightClass.toString());
            }

            if (submittedSearch) {
                queryParams.set('search', submittedSearch);
            }

            return authFetch(`http://localhost:8000/draft/${params.draftId}/draftableFighters?${queryParams.toString()}`).then(r => r.json());
        },
        placeholderData: keepPreviousData,
    })

    // Fetch League Info to get team names, league capacity, etc.
    const { data: leagueData } = useQuery<LeagueInfo>({
        queryKey: ['League', params.leagueId],
        queryFn: () => authFetch(`http://localhost:8000/league/${params.leagueId}`).then(r => r.json()),
    })

    // Fetch Draft Order.
    const { data: draftOrderData } = useQuery<DraftOrderTeam[]>({
        queryKey: ['draft', params.draftId, 'draftOrder'],
        queryFn: () => authFetch(`http://localhost:8000/draft/${params.draftId}/draftOrder`).then(r => r.json()),
    })

    // Fetch Past Picks to show draft history on the right column
    const { data: pastPicksData } = useQuery({
        queryKey: ['draft', params.draftId, 'pastPicks'],
        queryFn: () => authFetch(`http://localhost:8000/draft/${params.draftId}/pastPicks`).then(r => r.json()),
    })

    // Calculate how many picks until user's next pick based on current pick and draft order.
    const nextUserPick = draftOrderData && draftStateData ? draftOrderData.find((pick) => pick.team.id === draftStateData.user_team_id && pick.pick_num >= draftStateData.current_pick) : undefined;
    const picksUntilUserNextPick = nextUserPick && draftStateData ? nextUserPick.pick_num - draftStateData.current_pick : undefined;

    // Removed the sequential useEffect because the WebSocket now invalidates all queries in parallel.

    // Effect to update the past picks reference when new picks are added to trigger animations in the AnimatedList component
    useEffect(() => {
        if (!pastPicksData) return;

        setDraftHistory(pastPicksData.map((pick: any) => ({
            id: pick.pick_num,
            round: Math.ceil(pick.pick_num / leagueData?.league.capacity!),
            pick: pick.pick_num,
            user: pick.team.name || 'Unknown Team',
            fighter: pick.fighter.full_name,
            wc: pick.fighter.weight,
        })) || []);
    }, [pastPicksData, leagueData?.league.capacity]);

    useEffect(() => {
        if (draftStateData?.user_team_id) {
            setSelectedTeamId(draftStateData.user_team_id);
        }
    }, [draftStateData?.user_team_id]);

    // Fetch selected team's roster data to show in the left column. This query depends on 'selectedTeamId' and will only run when it's set.
    const {data: rosterData} = useQuery<TeamDataResponse>({
        queryKey: ['team', selectedTeamId],
        queryFn: () => authFetch(`http://localhost:8000/team/${selectedTeamId}`).then(r => r.json()),
        enabled: !!selectedTeamId, // Only run this query if selectedTeamId is available
    })

    const USERTEAMID = draftStateData ? draftStateData.user_team_id : undefined;
    const canDraft = draftStateData?.team_to_pick_id === USERTEAMID;

    // Handles errors that can occur during the drafting process 
    const handleDraftingErrors = (error: any) => {
        if (error.code === 'not_your_turn') {
            alert("It's not your turn to draft!");
        } else if (error.code === 'weight_class_and_flex_full') {
            alert(error.detail + " Please choose another fighter in a different weight class.");
        } else if (error.code === 'fighter_already_drafted') {
            alert("This fighter has already been drafted by another team.");
        } else if (error.code === 'no_available_fighters') {
            alert("No available fighters to draft.");
        } else if (error.code === 'draft_not_live') {
            alert("Draft has not yet started.");
        } else {
            alert("An unexpected error occurred while drafting. Please try again.");
        }
    }

    // Handles successful draft picks and draft completion
    const handleDraftingSuccess = (data: any) => {
        if (data.code === 'draft_completed') {
            alert("Draft is now completed!");
        } else if (data.code === 'pick_successful') {
            alert("Pick successful!");
        }
    }

    const invalidateDraftQueries = (params: { draftId?: string }) => {
        const draftId = params.draftId;
        if (!draftId) return;

        queryClient.invalidateQueries({ queryKey: ['draft', draftId, 'state'] });
        queryClient.invalidateQueries({ queryKey: ['draft', draftId, 'draftableFighters'] });
        queryClient.invalidateQueries({ queryKey: ['draft', draftId, 'pastPicks'] });
        queryClient.invalidateQueries({ queryKey: ['team', selectedTeamId] });
    };

    const draftFighterMutation = useMutation({
        mutationFn: async (payload: DraftFighterPayload) => {
        const response = await authFetch(`http://localhost:8000/draft/${params.draftId}/pick`, {
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
            handleDraftingErrors(error);
        },
    
        onSuccess: (data) => {
            if (data.action_required === 'confirm_flex') {
                setPendingFlexFighterId(data.fighter_id);
                setFlexDialogOpen(true);
            };

            handleDraftingSuccess(data);
            invalidateDraftQueries(params);
        }
    })

    const draftFlexMutation = useMutation({
        mutationFn: async (payload: DraftFighterPayload) => {
        const response = await authFetch(`http://localhost:8000/draft/${params.draftId}/draftFlex`, {
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
            handleDraftingErrors(error);
        },
    
        onSuccess: (data) => {
            handleDraftingSuccess(data);
            invalidateDraftQueries(params);
        }
    })

    // Time derived from server to show countdowns, current pick, etc.
    //get current time in seconds
    const now = () => Math.floor(Date.now() / 1000);
    const [currentTime, setCurrentTime] = useState(now());
    useEffect(() => {
        setInterval(() => setCurrentTime(now()), 1000);
    }, []);
    const elapsedTime = currentTime - Math.floor(new Date(draftStateData?.pick_start_time || '').getTime() / 1000);
    const timeLeft = 60 - elapsedTime;
    // get current round from current pick and league capacity
    const currentRound = Math.ceil((draftStateData?.current_pick || 0) / (leagueData?.league.capacity || 1));    // Mock Roster Data (1 per Weight Class)
    const COLUMN_HEIGHT = '885px';

    // Draft history to display to animated list of past picks
    const [draftHistory, setDraftHistory] = useState(
        pastPicksData?.map((pick: any) => ({
            id: pick.pick_num,
            round: Math.ceil(pick.pick_num / leagueData?.league.capacity!),
            pick: pick.pick_num,
            user: pick.team.name || 'Unknown Team',
            fighter: pick.fighter.full_name,
            wc: pick.fighter.weight,
        })) || []
    );

    // Transform raw API data into row format for the DataGrid
    // Convert weight class names to numeric values using the weightClassMap
    const allRows = draftableFightersData?.results?.map((item, index) => ({
        id: item.fighter.fighter_id,
        weightClass: item.fighter.slot_type,
        fighter: item.fighter.full_name,
        last: item.fantasy?.last_fight_points.toFixed(1) ?? '0',
        average: item.fantasy?.average_points.toFixed(1) ?? '0',
    })) || [];

    // Filter rows based on selected weight class
    // If selectedWeightClass is empty string, show all fighters
    // Otherwise, only show fighters matching the selected weight class number
    const filteredRows = selectedWeightClass === '' 
        ? allRows 
        : allRows.filter(row => row.weightClass === selectedWeightClass);

    const handleDraftPick = ({
        fighterId,
        fighterName,
        weightClass,
    }: {
        fighterId: number;
        fighterName: string;
        weightClass: string;
    }) => {
        if (!canDraft) return;

        setPendingDraftPick({
            fighter_id: fighterId,
            fighter_name: fighterName,
            weight_class: weightClass,
        });
        setConfirmDraftDialogOpen(true);
    };

    const handleConfirmDraftPick = () => {
        if (!pendingDraftPick || !draftStateData?.user_team_id) return;

        draftFighterMutation.mutate({
            team_id: draftStateData.user_team_id,
            fighter_id: pendingDraftPick.fighter_id,
        });

        setConfirmDraftDialogOpen(false);
        setPendingDraftPick(null);
    };

    const handleCancelDraftPick = () => {
        setConfirmDraftDialogOpen(false);
        setPendingDraftPick(null);
    };
    const handleRosterDialogOpen = () => setRosterDialogOpen(true);
    const handleRosterDialogClose = () => setRosterDialogOpen(false);

    const handleDraftFlex = () => {
        if (!pendingFlexFighterId) return;
        setFlexDialogOpen(false);
        draftFlexMutation.mutate({
            team_id: draftStateData?.user_team_id!,
            fighter_id: pendingFlexFighterId,
        });
        setPendingFlexFighterId(null);
    };

    const handleFlexDialogCancel = () => {
        setFlexDialogOpen(false);
        setPendingFlexFighterId(null);
    };

    const baseColumns: GridColDef[] = [
        { field: 'weightClass', headerName: 'WC', flex: 0.6, minWidth: 60 },
        { field: 'fighter', headerName: 'Fighter', flex: isMobile ? 1.2 : 2, minWidth: 100 },
    ];

    const desktopOnlyColumns: GridColDef[] = [
        { field: 'last', headerName: 'Lst', flex: 1, minWidth: 80 },
    ];

    const averageColumn: GridColDef = {
        field: 'average',
        headerName: 'Avg',
        flex: 1,
        minWidth: 80,
    };

    const draftColumn: GridColDef = {
        field: 'draft',
        headerName: '',
        flex: isMobile ? 0.75 : 0.9,
        minWidth: isMobile ? 70 : 110,
        sortable: false,
        filterable: false,
        disableColumnMenu: true,
        align: 'center',
        headerAlign: 'center',
        headerClassName: 'draft-action-header',
        renderHeader: () => null,
        renderCell: DraftButton,
    };

    const columns: GridColDef[] = isMobile
        ? [...baseColumns, draftColumn]
        : [...baseColumns, ...desktopOnlyColumns, averageColumn, draftColumn];

    // Mock Recent Pick - Static
    // Mock Header Data
    const draftState = {
        round: 2,
        totalRounds: 16,
        timer: '00:13',
        currentPick: {
            number: 27,
            team: 'Team Trey',
            avatarColor: 'brand.main'
        },
        upcomingPicks: [
            { number: 28, team: 'Team Adan', avatarColor: 'brandAlpha50.main' },
            { number: 29, team: 'Team Adan', avatarColor: 'brandAlpha50.main' },
            { type: 'round_separator', number: 3 },
            { number: 30, team: 'Team Adan', avatarColor: 'brandAlpha50.main' },
            { number: 31, team: 'Team Adan', avatarColor: 'brandAlpha50.main' },
            { number: 32, team: 'Team Adan', avatarColor: 'brandAlpha50.main' },
            { number: 33, team: 'Team Adan', avatarColor: 'brandAlpha50.main' },
            { number: 34, team: 'Team Adan', avatarColor: 'brandAlpha50.main' },
            { number: 35, team: 'Team Adan', avatarColor: 'brandAlpha50.main' },
            { type: 'round_separator', number: 4 },
            { number: 36, team: 'Team Adan', avatarColor: 'brandAlpha50.main' },
        ]
    };
    const upcomingPickItems = draftState.upcomingPicks.filter(
        (item: any) => item.type !== 'round_separator'
    );

    return (
        <ListPageLayout>
            <Stack spacing={1}>
            {/* TOP COLUMN */}
            {/* Contains the Timer, "On The Clock", and "Upcoming Picks" list */}
            <Box sx={{
                p: 2,
                backgroundColor: 'dashboardBlack.main',
                borderRadius: 4,
                display: { xs: 'block', md: 'none' },
            }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, overflow: 'hidden' }}>
                    <Paper sx={{
                        width: { xs: 104, sm: 116 },
                        height: { xs: 96, sm: 104 },
                        p: 1,
                        borderRadius: 2,
                        bgcolor: 'whiteAlpha20.main',
                        border: '1px solid',
                        borderColor: 'whiteAlpha20.main',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'center',
                        justifyContent: 'center',
                        gap: 0.5,
                        flexShrink: 0,
                    }}>
                        <Typography variant="caption" sx={{ color: 'text.secondary', lineHeight: 1 }}>
                            Pick {draftState.currentPick.number}
                        </Typography>
                        <Typography variant="body2" sx={{ color: 'brand.main', fontWeight: 700, lineHeight: 1 }}>
                            {timeLeft > 0 ? timeLeft : '00:00'}
                        </Typography>
                        <Typography
                            variant="caption"
                            sx={{
                                color: 'white',
                                lineHeight: 1.2,
                                maxWidth: '100%',
                                display: '-webkit-box',
                                WebkitBoxOrient: 'vertical',
                                WebkitLineClamp: 2,
                                overflow: 'hidden',
                                wordBreak: 'break-word',
                                textAlign: 'center',
                            }}
                        >
                            {draftState.currentPick.team}
                        </Typography>
                    </Paper>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, overflow: 'hidden' }}>
                        {upcomingPickItems.map((item: any, index: number) => (
                            <Paper key={item.number} sx={{
                                width: { xs: 28, sm: 32 },
                                height: { xs: 96, sm: 104 },
                                borderRadius: 2,
                                bgcolor: index % 2 === 0 ? 'gray900.main' : 'whiteAlpha20.main',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                flexShrink: 0,
                            }}>
                                <Typography variant="caption" sx={{ color: 'white', fontSize: '0.7rem', textAlign: 'center' }}>
                                    {item.number}
                                </Typography>
                            </Paper>
                        ))}
                    </Box>
                </Box>
            </Box>
            <Box sx={{
                p: 2,
                py: 4, // Increased vertical padding for height
                backgroundColor: 'dashboardBlack.main',
                borderRadius: 4,
                display: { xs: 'none', md: 'block' },
            }}>
                <Grid container spacing={2}>

                    {/* Shows current round and countdown */}
                    <Grid size={{ xs: 12, md: 3, lg: 2 }}>
                        <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                            <Typography variant="caption" sx={{ color: 'white', display: 'block', mb: -0.5, fontWeight: 600, fontSize: '0.85rem' }}>
                                ROUND {currentRound} OF {10}
                            </Typography>
                            <Box sx={{ width: 'fit-content' }}>
                                <Typography variant="h2" sx={{ color: 'brand.main', fontSize: '2.5rem', lineHeight: 1 }}>
                                    {timeLeft > 0 ? timeLeft : '00:00'}
                                </Typography>
                                <Box sx={{ height: 2, width: '100%', bgcolor: 'brand.main', mt: 1 }} />
                            </Box>
                        </Box>
                    </Grid>


                    {/* 2. On The Clock Section */}
                    <Grid size={{ xs: 12, md: 3, lg: 3 }}>
                        <Paper sx={{
                            p: 2,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 3,
                            borderRadius: 3,
                            bgcolor: 'whiteAlpha20.main',
                            border: '1px solid',
                            borderColor: 'whiteAlpha20.main',
                            width: '100%', // Ensure paper takes full width of grid item
                            height: '100%' // Ensure paper takes full height for same-height effect
                        }}>
                            <Avatar sx={{ width: 64, height: 64, bgcolor: draftState.currentPick.avatarColor, fontSize: '1.5rem' }}>
                                {/* Placeholder icon or initial */}
                            </Avatar>
                            <Box>
                                <Typography variant="body2" sx={{ color: 'text.secondary', mb: 0.5 }}>
                                    On The Clock: Pick {draftState.currentPick.number === null ? 'N/A' : draftState.currentPick.number}
                                </Typography>
                                <Typography variant="h3" sx={{ color: 'white' }}>
                                    {draftState.currentPick.team}
                                </Typography>
                            </Box>
                        </Paper>
                    </Grid>


                    {/* Upcoming Picks List */}
                    {/* Uses 'overflowX' to scroll sideways for who picks next */}
                    <Grid size={{ xs: 12, md: 6, lg: 7 }}>
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', justifyContent: 'flex-start', overflowX: 'hidden', pb: 1, width: '100%' }}>
                            {draftState.upcomingPicks.map((item: any, index) => {
                                if (item.type === 'round_separator') {
                                    return (
                                        <Box key={`sep-${index}`} sx={{ textAlign: 'center', px: 1, flexShrink: 0 }}>
                                            <Typography variant="caption" sx={{ color: 'text.secondary', display: 'block', fontSize: '0.7rem' }}>
                                                ROUND
                                            </Typography>
                                            <Typography variant="h4" sx={{ color: 'white', fontWeight: 'bold' }}>
                                                {item.number}
                                            </Typography>
                                        </Box>
                                    );
                                }
                                // Ignores round seperators to for upcoming picks to alternate colors
                                const pickItems = draftState.upcomingPicks.filter((i: any) => i.type !== 'round_separator');
                                const pickIndex = pickItems.indexOf(item);

                                return (
                                    <Paper key={item.number} sx={{
                                        width: 120,
                                        p: 1.5,
                                        borderRadius: 3,
                                        bgcolor: pickIndex % 2 === 0 ? 'gray900.main' : 'whiteAlpha20.main', // Alternating Light -> Dark (ignoring separators)
                                        textAlign: 'center',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        gap: 1,
                                        flexShrink: 0
                                    }}>
                                        <Typography variant="caption" sx={{ color: 'white', fontWeight: 600 }}>
                                            Pick {item.number}
                                        </Typography>
                                        <Avatar sx={{ width: 32, height: 32, bgcolor: item.avatarColor, fontSize: '0.8rem' }} />
                                        <Typography variant="caption" sx={{ color: 'text.secondary', fontSize: '0.7rem', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100%' }}>
                                            {item.team}
                                        </Typography>
                                    </Paper>
                                );
                            })}
                        </Box>
                    </Grid>
                </Grid>
            </Box>


            {/*Splits into 3 columns here: Roster | Draft Board | History */}
            <Grid container spacing={{ xs: .5, sm: 1 }} sx={{ height: COLUMN_HEIGHT, alignItems: 'stretch' }}>


                {/* Left Column - Current Roster */}
                <Grid size={{ md: 3 }} sx={{ display: { xs: 'none', md: 'flex' }, minHeight: 0 }}>
                    <Box sx={{
                        borderRadius: 4,
                        backgroundColor: 'dashboardBlack.main',
                        p: 2,
                        display: 'flex',
                        flexDirection: 'column',
                        height: COLUMN_HEIGHT,
                        maxHeight: COLUMN_HEIGHT,
                        minHeight: 0,
                        width: '100%',
                    }}>
                        <Box sx={{ mb: 2, 
                                display: 'flex', 
                                flexDirection: 'column', 
                                alignItems: 'center', 
                                gap: 2,
                                }}>
                            <Typography variant="h3" sx={{ fontSize: '1rem', color: 'text.secondary'}}>
                                View Rosters
                            </Typography>
                            <Select
                                value={selectedTeamId ?? ''}
                                onChange={(e) => setSelectedTeamId(Number(e.target.value))}
                                sx={{
                                    width: '100%',
                                    color: 'white',
                                }}
                            >
                                {leagueData?.teams.map((team) => (
                                    <MenuItem key={team.id} value={team.id}>
                                        {team.name}
                                    </MenuItem>
                                ))}
                            </Select>
                        </Box>
                        {/* List of roster members */}
                        <Stack
                            spacing={1}
                            sx={{
                                flex: 1,
                                height: '100%',
                                minHeight: 0,
                                overflowY: 'auto',
                                scrollbarWidth: 'none', // Firefox
                                '&::-webkit-scrollbar': {
                                    display: 'none', // Chrome, Safari, Edge
                                },
                                msOverflowStyle: 'none', // IE
                            }}
                        >
                            {rosterData?.roster.map((slot, index) => (
                                <DraftPlayerCard
                                    key={index}
                                    name={slot.fighter? slot.fighter.full_name : 'Empty Slot'}
                                    subtitle={slot.fighter ? `Avg: ${slot.fantasy?.average_points.toFixed(1) ?? '0.0'} | Last: ${slot.fantasy?.last_fight_points.toFixed(1) ?? '0.0'}` : 'No Fighter Drafted'}
                                    weightClass={slot.slot}
                                    variant="roster"
                                />
                            ))}
                        </Stack>
                    </Box>
                </Grid>

                {/* Center Column - Draft Board */}
                <Grid size={{ xs: 12, sm: 12, md: 6 }} sx={{ display: 'flex', minHeight: 0 }}>
                    <Paper sx={{
                        borderRadius: 4,
                        backgroundColor: 'dashboardBlack.main',
                        p: 2, // Internal padding
                        display: 'flex',
                        flexDirection: 'column',
                        height: COLUMN_HEIGHT,
                        maxHeight: COLUMN_HEIGHT,
                        minHeight: 0,
                        width: '100%',
                    }}>
                        <Stack spacing={3} sx={{ height: '100%', minHeight: 0 }}>

                            {/* On The Clock */}
                            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 2 }}>
                                <Avatar sx={{ bgcolor: 'brand.main', width: 40, height: 40 }}></Avatar>
                                <Box>
                                    <Typography variant="h3" sx={{ fontSize: '1.2rem', color: 'white' }}>
                                        {picksUntilUserNextPick === 0 ? 'On the clock NOW!' : `On the clock in `}
                                        <Typography component="span" variant="h3" sx={{ fontSize: '1.2rem', fontWeight: 'bold', color: 'brand.main' }}>
                                            {picksUntilUserNextPick !== 0 && picksUntilUserNextPick}
                                        </Typography>
                                        {picksUntilUserNextPick !== 0 && ` Pick${picksUntilUserNextPick !== 1 ? 's' : ''}`}
                                    </Typography>
                                </Box>
                            </Box>

                            {/* Draftable Fighters Title & Weight Classes Filter & View Roster */}
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                {/* Left Side: Draftable Fighters Title (hidden on xs/sm) */}
                                <Typography
                                    variant="h3"
                                    sx={{
                                        fontSize: '1rem',
                                        color: 'text.secondary',
                                        display: { xs: 'none', md: 'block' },
                                    }}
                                >
                                    Draftable Fighters
                                </Typography>

                                {/* Right Side: Weight Classes Filter & View Roster Button */}
                                <Box sx={{ 
                                    display: 'flex', 
                                    gap: 2, 
                                    alignItems: 'center', 
                                    marginLeft: { xs: 0, md: 'auto' },
                                    width: { xs: '100%', md: 'auto' },
                                    justifyContent: { xs: 'space-between', md: 'flex-start' }
                                }}>
                                {/* Weight Classes Filter */}
                                <FormControl size="small" sx={{ width: 'fit-content' }}>
                                    <Select
                                        displayEmpty
                                        value={selectedWeightClass}
                                        onChange={(e) => setSelectedWeightClass(e.target.value)}
                                        sx={{
                                            minWidth: 160,
                                            borderRadius: 2,
                                            height: 40,
                                            // Quick inline style to match dark theme look for select
                                            '.MuiOutlinedInput-notchedOutline': { borderColor: 'rgba(255,255,255,0.2)' },
                                            color: 'white',
                                            '& .MuiSvgIcon-root': { color: 'white' }
                                        }}
                                    >
                                        {/* "All Weight Classes" menu item - resets filter to show all fighters */}
                                        <MenuItem value="">All Weight Classes</MenuItem>
                                        
                                        {/* Individual weight class menu items with numeric values - clicking updates selectedWeightClass state */}
                                        <MenuItem value="HW">Heavyweight (265)</MenuItem>
                                        <MenuItem value="LHW">Light Heavyweight (205)</MenuItem>
                                        <MenuItem value="MW">Middleweight (185)</MenuItem>
                                        <MenuItem value="WW">Welterweight (170)</MenuItem>
                                        <MenuItem value="LW">Lightweight (155)</MenuItem>
                                        <MenuItem value="FW">Featherweight (145)</MenuItem>
                                        <MenuItem value="BW">Bantamweight (135)</MenuItem>
                                        <MenuItem value="FLW">Flyweight (125)</MenuItem>
                                        <MenuItem value="SW">Strawweight (115)</MenuItem>
                                    </Select>
                                </FormControl>

                                <TextField
                                    id="outlined-basic"
                                    label="Search by fighter name"
                                    variant="outlined"
                                    value={typedSearch}
                                    onChange={(event) => setTypedSearch(event.target.value)}
                                    onKeyDown={handleSearchKeyDown}
                                    sx={{
                                        "& .MuiInputBase-root": {
                                            bgcolor: 'hsla(216, 33%, 3%, 1)',
                                        },
                                    }}
                                    slotProps={{
                                        input: {
                                            endAdornment: (
                                                <InputAdornment position="end" >
                                                    <IconButton
                                                        aria-label="search fighters"
                                                        onClick={handleSearchSubmit}
                                                        edge="end"

                                                    >
                                                        <SearchIcon sx={{ color: 'common.white' }} />
                                                    </IconButton>
                                                </InputAdornment>
                                            ),
                                        },
                                    }}
                                ></TextField>

                                {/* View Roster Button (xs/sm only) */}
                                <Button
                                    variant="contained"
                                    color="whiteAlpha20"
                                    size="small"
                                    onClick={handleRosterDialogOpen}
                                    sx={{ display: { xs: 'inline-flex', md: 'none' }, padding: '4px 12px', fontSize: '0.75rem' }}
                                >
                                    View Roster
                                </Button>
                                </Box>
                            </Box>

                            {/* Available Fighters */}
                            <Box sx={{ flex: 1, overflow: 'hidden', minHeight: 0 }}>
                                {/* DataGrid displays filtered fighter rows based on selected weight class */}
                                <DataGrid //displays the table 
                                        rows={filteredRows} 
                                        columns={columns} 
                                        
                                        pagination
                                        paginationMode="server"
                                        paginationModel={paginationModel}
                                        onPaginationModelChange={setPaginationModel}
                                        rowCount={draftableFightersData?.count ?? 0}
                                        pageSizeOptions={[25, 50, 100]}
                                        loading={isDraftableFightersPending}
                                        
                                        disableRowSelectionOnClick // removes checkboxes
                                        disableColumnSorting // removes sorting. (if adding filtering remove this)
                                        
                                        //Allows alternating colored rows
                                        getRowClassName={(params) =>
                                            params.indexRelativeToCurrentPage % 2 === 0 ? "even-row" : "odd-row"
                                        }
                                        
                                        // STYLING
                                        sx={(theme) => ({
                                            height: '100%',
                                            
                                            //Alternating row colors
                                            "& .MuiDataGrid-row.even-row":{
                                                backgroundColor: (theme.palette.brand as any).dark,
                                            },
                                            "& .MuiDataGrid-row.odd-row":{
                                                backgroundColor: "transparent",
                                            },

                                            //Text Styling     
                                            // Hides Unwanted parts of the grid
                                            // Sort Icons and Interactive elements from them
                                            "& .MuiDataGrid-iconButtonContainer": {display: "none"},
                                            "& .MuiDataGrid-sortIcon": {display: "none"},
                                            "& .draft-action-header .MuiDataGrid-columnHeaderTitle": {display: "none"},
                            
                                        })}      
                                />
                            </Box>
                        </Stack>
                    </Paper>
                </Grid>
                {/* Column 3: Past Picks History */}
                <Grid size={{ md: 3 }} sx={{ display: { xs: 'none', md: 'flex' }, minHeight: 0 }}>
                    <Box sx={{
                        height: COLUMN_HEIGHT,
                        maxHeight: COLUMN_HEIGHT,
                        display: 'flex',
                        flexDirection: 'column',
                        width: '100%',
                        borderRadius: 4,
                        backgroundColor: 'dashboardBlack.main',
                        p: 2,
                        overflow: 'hidden',
                        minHeight: 0,
                    }}>
                        {/* Header with Test buttons */}
                        <Box sx={{ mb: 2, 
                                display: 'flex', 
                                justifyContent: 'space-between', 
                                alignItems: 'center', 
                                overflow: 'hidden' 
                            }}>
                            <Typography variant="h3" sx={{ fontSize: '1rem', color: 'text.secondary' }}>
                                Past Picks
                            </Typography>
                        </Box>
                        <Box sx={{ 
                            flex: 1, 
                            minHeight: 0, 
                            overflowY: 'auto',
                            scrollbarWidth: 'none', // Firefox
                            '&::-webkit-scrollbar': {
                                display: 'none', // Chrome, Safari, Edge
                            },
                            msOverflowStyle: 'none', // IE
                        }}>
                            <AnimatedList<DraftHistoryItem>
                                items={draftHistory}
                                gap={8}
                                renderItem={(item) => (
                                    <DraftPlayerCard
                                        name={item.fighter}
                                        subtitle={`R${item.round}, P${item.pick} | ${item.user}`}
                                        weightClass={item.wc}
                                        variant="history"
                                    />
                                )}
                            />
                        </Box>
                        </Box>
                </Grid>
            </Grid>
            </Stack>
            <Dialog
                open={rosterDialogOpen}
                onClose={handleRosterDialogClose}
                fullWidth
                maxWidth="sm"
                sx={{ display: { xs: 'block', md: 'none' } }}
                BackdropProps={{
                    sx: {
                        backdropFilter: 'blur(6px)',
                        backgroundColor: 'rgba(0, 0, 0, 0.4)',
                    },
                }}
                PaperProps={{
                    sx: {
                        backgroundColor: 'dashboardBlack.main',
                        borderRadius: 3,
                    },
                }}
            >
                <DialogTitle sx={{ color: 'white' }}>
                    View Rosters
                </DialogTitle>
                <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 1, maxHeight: '70vh', overflowY: 'auto' }}>
                    <FormControl fullWidth>
                        <Select
                            value={selectedTeamId ?? ''}
                            onChange={(e) => setSelectedTeamId(Number(e.target.value))}
                            sx={{
                                color: 'white',
                            }}
                        >
                            {leagueData?.teams.map((team) => (
                                <MenuItem key={team.id} value={team.id}>
                                    {team.name}
                                </MenuItem>
                            ))}
                        </Select>
                    </FormControl>
                    {rosterData?.roster.map((slot, index) => (
                        <DraftPlayerCard
                            key={index}
                            name={slot.fighter ? slot.fighter.full_name : 'Empty Slot'}
                            subtitle={slot.fighter ? `Avg: ${slot.fantasy?.average_points.toFixed(1) ?? '0.0'} | Last: ${slot.fantasy?.last_fight_points.toFixed(1) ?? '0.0'}` : 'No Fighter Drafted'}
                            weightClass={slot.slot}
                            variant="roster"
                        />
                    ))}
                </DialogContent>
            </Dialog>

            {/* Draft Confirmation Dialog */}
            <Dialog
                open={confirmDraftDialogOpen}
                onClose={handleCancelDraftPick}
                maxWidth="sm"
                fullWidth
            >
                <DialogTitle sx={{
                    fontWeight: 700,
                    fontSize: '1.3rem',
                    textAlign: 'center',
                    pb: 1
                }}>
                    Confirm Draft Pick
                </DialogTitle>
                <DialogContent sx={{ pt: 2 }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                        <Typography sx={{ fontSize: '1rem', textAlign: 'center', color: 'text.secondary' }}>
                            Are you sure you want to draft:
                        </Typography>
                        <Box sx={{ p: 2, bgcolor: 'rgba(255, 255, 255, 0.05)', borderRadius: 1.5 }}>
                            <Typography sx={{ fontSize: '0.875rem', color: 'text.secondary', mb: 0.5, letterSpacing: '0.05em', fontWeight: 600 }}>
                                Fighter
                            </Typography>
                            <Typography sx={{ fontSize: '1.1rem', fontWeight: 600 }}>
                                {pendingDraftPick?.fighter_name}
                            </Typography>
                            <Typography sx={{ fontSize: '0.95rem', color: 'text.secondary', mt: 0.5 }}>
                                Weight Class: {pendingDraftPick?.weight_class}
                            </Typography>
                        </Box>
                    </Box>
                </DialogContent>
                <DialogActions sx={{ gap: 1, p: 2.5, borderTop: '1px solid rgba(255, 255, 255, 0.1)' }}>
                    <Button
                        onClick={handleCancelDraftPick}
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
                        onClick={handleConfirmDraftPick}
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
                        Draft
                    </Button>
                </DialogActions>
            </Dialog>

            {/* Flex Confirmation Dialog */}
            <Dialog
                open={flexDialogOpen}
                onClose={handleFlexDialogCancel}
                PaperProps={{
                    sx: {
                        backgroundColor: 'dashboardBlack.main',
                        borderRadius: 3,
                    },
                }}
            >
                <DialogTitle sx={{ color: 'white' }}>
                    Confirm FLEX Assignment
                </DialogTitle>
                <DialogContent sx={{ color: 'white' }}>
                    <Typography>
                        This weight class is full. FLEX is available. Do you want to assign this fighter to FLEX?
                    </Typography>
                </DialogContent>
                <Box sx={{ p: 2, display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                    <Button
                        variant="contained" 
                        color="whiteAlpha20"
                        onClick={handleFlexDialogCancel}
                        sx={{
                            borderColor: 'gray900.main',
                            '&:hover': {
                                borderColor: 'gray800.main'
                            }
                        }}
                        
                    >
                        Cancel
                    </Button>
                    <Button
                        variant="contained"
                        color="brandAlpha50"
                        onClick={handleDraftFlex}
                        sx={{ 
                        borderColor: 'brand.light',
                        '&:hover': {
                            borderColor: 'brand.main'
                        }                        
                    }}
                    >
                        Draft FLEX
                    </Button>
                </Box>
            </Dialog>
        </ListPageLayout>
    );
}
