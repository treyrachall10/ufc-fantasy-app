import { Box, Grid, Paper, Stack, Typography, FormControl, Select, MenuItem, Avatar, Button, Menu, Dialog, DialogTitle, DialogContent, useMediaQuery } from '@mui/material';
import ListPageLayout from '../components/layout/ListPageLayout';
import FighterTable from '../components/dataGrid/FighterTable';
import DraftPlayerCard from '../components/Draftcards/DraftPlayerCard';
import { useEffect, useState } from 'react';
import AnimatedList from '../components/Animations/AnimatedList';
import { useQuery } from '@tanstack/react-query';
import { authFetch } from '../auth/authFetch';
import { useParams } from 'react-router-dom';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';
import { LeagueInfo, TeamDataResponse } from '../types/types';

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
    const isMobile = useMediaQuery('(max-width: 600px)');
    
    // Draft Button Renderer for DataGrid - Calls the handleDraftPick function with the fighter's ID when clicked.
    const DraftButton = (params: GridRenderCellParams) => {
        return (
            <Button
                variant="contained"
                color="whiteAlpha20"
                onClick={() => handleDraftPick(Number(params.id))}
                size={isMobile ? 'small' : undefined}
                sx={{
                    textWrap: 'nowrap',
                    borderColor: 'gray900.main',
                    '&:hover': { borderColor: 'gray800.main' },
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
    const { data: draftStateData, isPending: isDraftStatePending, error: draftStateError} = useQuery<DraftState>({
        queryKey: ['draft', params.draftId, 'state'],
        queryFn: () => authFetch(`http://localhost:8000/draft/${params.draftId}/state`).then(r => r.json()),
        refetchInterval: 1000, // Refetch every 1000 milliseconds (1 second)
    })

    // Fetch Draftable Fighters for Draft Board
    const { data: draftableFightersData, isPending: isDraftableFightersPending, error: draftableFightersError} = useQuery<DraftableFighter[]>({
        queryKey: ['draft', params.draftId, 'draftableFighters'],
        queryFn: () => authFetch(`http://localhost:8000/draft/${params.draftId}/draftableFighters`).then(r => r.json()),
    })

    // Fetch League Info to get team names, league capacity, etc.
    const { data: leagueData, isPending: isLeagueDataPending, error: leagueDataError} = useQuery<LeagueInfo>({
        queryKey: ['League', params.leagueId],
        queryFn: () => authFetch(`http://localhost:8000/league/${params.leagueId}`).then(r => r.json()),
    })

    // Fetch Past Picks to show draft history on the right column
    const { data: pastPicksData, isPending: isPastPicksPending, error: pastPicksError} = useQuery({
        queryKey: ['draft', params.draftId, 'pastPicks'],
        queryFn: () => authFetch(`http://localhost:8000/draft/${params.draftId}/pastPicks`).then(r => r.json()),
    })

    const [selectedTeamId, setSelectedTeamId] = useState<number | undefined>();
    const [rosterDialogOpen, setRosterDialogOpen] = useState(false);
    
    // Set default team to user's own team when draft state loads
    useEffect(() => {
        if (draftStateData?.user_team_id) {
            setSelectedTeamId(draftStateData.user_team_id);
        }
    }, [draftStateData?.user_team_id]);

    // Log when selected team changes
    const selectedTeamName = leagueData?.teams.find((team) => team.id === selectedTeamId)?.name || 'Your Team';
    useEffect(() => {
        console.log("Selected Team:", selectedTeamName);
    }, [selectedTeamName]);

    // Fetch selected team's roster data to show in the left column. This query depends on 'selectedTeamId' and will only run when it's set.
    const {data: rosterData, isPending: isRosterDataPending, error: rosterDataError} = useQuery<TeamDataResponse>({
        queryKey: ['team', selectedTeamId],
        queryFn: () => authFetch(`http://localhost:8000/team/${selectedTeamId}`).then(r => r.json()),
        enabled: !!selectedTeamId, // Only run this query if selectedTeamId is available
    })

    // State for weight class filter - holds the selected weight class number or empty string for all
    const [selectedWeightClass, setSelectedWeightClass] = useState('');

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

    // Mock Draft History (Not really in use atm)
    const [draftHistory, setDraftHistory] = useState([
        { id: 106, round: 1, pick: 6, user: 'Team Adan', fighter: 'Sean O\'Malley', wc: 'BW' },
        { id: 105, round: 1, pick: 5, user: 'Team Trey', fighter: 'Belal Muhammad', wc: 'WW' },
        { id: 104, round: 1, pick: 4, user: 'Team Chris', fighter: 'Ilia Topuria', wc: 'FW' },
        { id: 103, round: 1, pick: 3, user: 'Team Matt', fighter: 'Islam Makhachev', wc: 'LW' },
        { id: 102, round: 1, pick: 2, user: 'Team Adan', fighter: 'Alex Pereira', wc: 'LHW' },
        { id: 101, round: 1, pick: 1, user: 'Team Trey', fighter: 'Jon Jones', wc: 'HW' },
    ]);

    // Transform raw API data into row format for the DataGrid
    // Convert weight class names to numeric values using the weightClassMap
    const allRows = draftableFightersData?.map((item, index) => ({
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

    const handleDraftPick = (fighterId: number) => {
        console.log(`Drafting fighter with ID: ${fighterId}`);
    };
    const handleRosterDialogOpen = () => setRosterDialogOpen(true);
    const handleRosterDialogClose = () => setRosterDialogOpen(false);

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

    // 3. Helper Functions
    // This function adds a new mock pick to the TOP of the history list.
    const addPick = () => {
        const newPick = {
            id: Date.now(),
            round: 2,
            pick: 1,
            user: 'Team Adan',
            fighter: 'Illia Topuria',
            wc: 'FW',
        };
        // The new pick goes first '...draftHistory' keeps the old ones after it.
        setDraftHistory([newPick, ...draftHistory]);
    };


    const clearHistory = () => {
        setDraftHistory([]);
    };


    // Mock Recent Pick - Static
    const recentPick = {
        id: 106,
        round: 1,
        pick: 6,
        user: 'Team Adan',
        fighter: 'Illia Topuria',
        wc: 'FW',
    };

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
                                    On The Clock: Pick {draftState.currentPick.number}
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
                                        You're on the clock: 1 Pick
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
                                        pageSizeOptions={[15]}
                                        initialState={{
                                            pagination: { paginationModel: { pageSize: 15, page: 0 } },
                                        }}
                                        
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
                            <Box sx={{ display: 'flex', gap: 1 }}>
                                <Button onClick={clearHistory} variant="text" size="small" color="error" sx={{ minWidth: 'auto', px: 1 }}>
                                    Clear
                                </Button>
                                <Button onClick={addPick} variant="text" size="small" sx={{ color: 'white', minWidth: 'auto', px: 1 }}>
                                    Add
                                </Button>
                            </Box>
                        </Box>

                        {/* 
                            How the List Works:
                            1. We pass the 'draftHistory' list to it.
                            2. 'renderItem' tells it how to draw EACH box (using DraftPlayerCard).
                            3. The component handles all the slide-in/fade-out animations automatically!
                        */}
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
                            <AnimatedList
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
        </ListPageLayout>
    );
}
