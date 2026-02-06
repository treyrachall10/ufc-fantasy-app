import { Box, Grid, Paper, Stack, Typography, FormControl, Select, MenuItem, Avatar, Button, } from '@mui/material';
import ListPageLayout from '../components/layout/ListPageLayout';
import FighterTable from '../components/dataGrid/FighterTable';
import DraftPlayerCard from '../components/Draftcards/DraftPlayerCard';
import { useEffect, useState } from 'react';
import AnimatedList from '../components/Animations/AnimatedList';
import { useQuery } from '@tanstack/react-query';
import { authFetch } from '../auth/authFetch';
import { useParams } from 'react-router-dom';
import { DataGrid, GridColDef, GridRenderCellParams } from '@mui/x-data-grid';

// TypeScript interface for draft state
interface DraftState {
    draft_status: string;
    current_pick: number;
    pick_start_time: string;
    team_to_pick_id: number;
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
    
    // Draft Button Renderer for DataGrid - Calls the handleDraftPick function with the fighter's ID when clicked.
    const DraftButton = (params: GridRenderCellParams) => {
        return (
            <Button
                variant="contained"
                color="whiteAlpha20"
                onClick={() => handleDraftPick(Number(params.id))}
                sx={{
                    textWrap: 'nowrap',
                    borderColor: 'gray900.main',
                    '&:hover': { borderColor: 'gray800.main' },
                }}
            >
                Draft
            </Button>
        )
    }
    // Fetch Draft State Data in rolling intervals using refetchinterval to keep the timer, current pick, and status updated in real-time.
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
    console.log('Elapsed Time:', elapsedTime);
    const timeLeft = 60 - elapsedTime;
    console.log('Time Left:', timeLeft);

    // Mock Roster Data (1 per Weight Class)
    const ROSTER_SLOTS = [
        { id: 8, wc: 'HW', name: 'Jon Jones', round: 'R1', pick: 'P1' },
        { id: 7, wc: 'LHW', name: 'Alex Pereira', round: 'R2', pick: 'P1' },
        { id: 6, wc: 'MW', name: 'Dricus Du Plessis', round: 'R3', pick: 'P1' },
        { id: 5, wc: 'WW', name: 'Belal Muhammad', round: 'R4', pick: 'P1' },
        { id: 4, wc: 'LW', name: 'Islam Makhachev', round: 'R5', pick: 'P1' },
        { id: 3, wc: 'FW', name: 'Ilia Topuria', round: 'R6', pick: 'P1' },
        { id: 2, wc: 'BW', name: 'Sean O\'Malley', round: 'R7', pick: 'P1' },
        { id: 1, wc: 'FLW', name: 'Alexandre Pantoja', round: 'R8', pick: 'P1' },
    ];

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

    console.log('Selected Weight Class:', selectedWeightClass);
    console.log('Total Fighters:', allRows.length);
    console.log('Filtered Fighters:', filteredRows.length);

    const handleDraftPick = (fighterId: number) => {
        console.log(`Drafting fighter with ID: ${fighterId}`);
    };

    const columns: GridColDef[] = [
        { field: 'weightClass', headerName: 'WC', flex: 0.5, minWidth: 50 },
        { field: 'fighter', headerName: 'Fighter', flex: 2, minWidth: 150 },
        { field: 'last', headerName: 'Last Fight', flex: 1, minWidth: 100 },
        { field: 'average', headerName: 'Average', flex: 1, minWidth: 100 },
        {
            field: 'draft',
            headerName: '',
            flex: 0.9,
            minWidth: 110,
            sortable: false,
            filterable: false,
            disableColumnMenu: true,
            align: 'center',
            headerAlign: 'center',
            headerClassName: 'draft-action-header',
            renderHeader: () => null,
            renderCell: DraftButton,
        },
    ];

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

    return (
        <ListPageLayout sx={{ mt: 6 }}>

            {/* TOP COLUMN */}
            {/* Contains the Timer, "On The Clock", and "Upcoming Picks" list */}
            <Box sx={{
                mb: 3,
                p: 2,
                py: 4, // Increased vertical padding for height
                backgroundColor: 'dashboardBlack.main',
                borderRadius: 4,
            }}>
                <Grid container spacing={2}>

                    {/* Shows current round and countdown */}
                    <Grid size={{ xs: 12, md: 3, lg: 2 }}>
                        <Box sx={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
                            <Typography variant="caption" sx={{ color: 'white', display: 'block', mb: -0.5, fontWeight: 600, fontSize: '0.85rem' }}>
                                ROUND {draftState.round} OF {draftState.totalRounds}
                            </Typography>
                            <Box sx={{ width: 'fit-content' }}>
                                <Typography variant="h2" sx={{ color: 'brand.main', fontSize: '2.5rem', lineHeight: 1 }}>
                                    {draftState.timer}
                                </Typography>
                                <Box sx={{ height: 2, width: '100%', bgcolor: 'brand.main', mt: 1 }} />
                            </Box>
                        </Box>
                    </Grid>


                    {/* 2. On The Clock Section (Main Highlight) */}
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
                    <Grid size={{ xs: 12, md: 6, lg: 7 }} sx={{ overflow: 'hidden' }}>
                        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', justifyContent: 'flex-start', overflowX: 'auto', pb: 1, width: '100%' }}>
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
            <Grid container spacing={{ xs: .5, sm: 2 }} >


                {/* Left Column - Current Roster */}
                <Grid size={{ xs: 12, sm: 3 }}>
                    <Paper sx={{
                        height: '80vh',
                        borderRadius: 4,
                        backgroundColor: 'dashboardBlack.main',
                        p: 2,
                        display: 'flex',
                        flexDirection: 'column',
                    }}>
                        {/* Header */}
                        <Box sx={{ mb: 2 }}>
                            <Typography variant="h3" sx={{ fontSize: '1rem', color: 'text.secondary' }}>Current Roster:</Typography>
                        </Box>

                        {/* List of Players */}
                        <Stack spacing={0} sx={{ flex: 1, justifyContent: 'space-between' }}>
                            {ROSTER_SLOTS.map((slot) => (
                                <DraftPlayerCard
                                    key={slot.id}
                                    name={slot.name}
                                    subtitle={`${slot.round}, ${slot.pick} | Team Trey`}
                                    weightClass={slot.wc}
                                    variant="roster"
                                />
                            ))}
                        </Stack>
                    </Paper>
                </Grid>




                {/* Center Column - Draft Board */}
                <Grid size={{ xs: 12, sm: 6 }}>
                    <Paper sx={{
                        height: '80vh',
                        borderRadius: 4,
                        backgroundColor: 'dashboardBlack.main',
                        p: 2, // Internal padding
                        display: 'flex',
                        flexDirection: 'column'
                    }}>
                        <Stack spacing={3} sx={{ height: '100%' }}>

                            {/* Info & Filters */}
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>

                                {/* Left Side: Avatar & upcoming pick */}
                                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                                    <Avatar sx={{ bgcolor: 'brand.main', width: 40, height: 40 }}></Avatar>
                                    <Box>
                                        <Typography variant="h3" sx={{ fontSize: '1.2rem', color: 'white' }}>
                                            You're on the clock: 1 Pick
                                        </Typography>
                                    </Box>
                                </Box>

                                {/* Right Side: Filter Dropdown */}
                                <FormControl size="small">
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
                                    </Select>
                                </FormControl>
                            </Box>

                            {/* Available Fighters */}
                            <Box sx={{ flex: 1, overflow: 'hidden' }}>
                                {/* DataGrid displays filtered fighter rows based on selected weight class */}
                                <DataGrid //displays the table 
                                        rows={filteredRows} 
                                        columns={columns} 
                                        
                                        disableRowSelectionOnClick // removes checkboxes
                                        disableVirtualization // renders all rows on a page, prevents scrolling the grid to see rows
                                        disableColumnSorting // removes sorting. (if adding filtering remove this)
                                        
                                        //Allows alternating colored rows
                                        getRowClassName={(params) =>
                                            params.indexRelativeToCurrentPage % 2 === 0 ? "even-row" : "odd-row"
                                        }
                                        
                                        // STYLING
                                        sx={(theme) => ({
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
                <Grid size={{ xs: 12, sm: 3 }}>
                    <Paper sx={{
                        height: '80vh',
                        borderRadius: 4,
                        backgroundColor: 'dashboardBlack.main',
                        p: 2,
                        overflowY: 'auto'
                    }}>
                        {/* Header with Test buttons */}
                        <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Typography variant="h3" sx={{ fontSize: '1rem', color: 'text.secondary' }}>
                                Past Picks:
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
                        <AnimatedList
                            items={draftHistory}
                            renderItem={(item) => (
                                <Box sx={{ mb: 2 }}>
                                    <DraftPlayerCard
                                        name={item.fighter}
                                        subtitle={`R${item.round}, P${item.pick} | ${item.user}`}
                                        weightClass={item.wc}
                                        variant="history"
                                    />
                                </Box>
                            )}
                        /></Paper>
                </Grid>
            </Grid>
        </ListPageLayout>
    );
}
