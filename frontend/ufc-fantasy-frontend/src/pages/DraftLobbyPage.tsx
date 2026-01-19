import { Box, Grid, Paper, Stack, Typography, FormControl, Select, MenuItem, Avatar, Button, } from '@mui/material';
import ListPageLayout from '../components/layout/ListPageLayout';
import FighterTable from '../components/dataGrid/FighterTable';
import DraftPlayerCard from '../components/Draftcards/DraftPlayerCard';
import { useState } from 'react';
import AnimatedList from '../components/Animations/AnimatedList';

export default function DraftLobbyPage() {

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

    // Mock Draft History - Static
    const [draftHistory, setDraftHistory] = useState([
        { id: 106, round: 1, pick: 6, user: 'Team Adan', fighter: 'Sean O\'Malley', wc: 'BW' },
        { id: 105, round: 1, pick: 5, user: 'Team Trey', fighter: 'Belal Muhammad', wc: 'WW' },
        { id: 104, round: 1, pick: 4, user: 'Team Chris', fighter: 'Ilia Topuria', wc: 'FW' },
        { id: 103, round: 1, pick: 3, user: 'Team Matt', fighter: 'Islam Makhachev', wc: 'LW' },
        { id: 102, round: 1, pick: 2, user: 'Team Adan', fighter: 'Alex Pereira', wc: 'LHW' },
        { id: 101, round: 1, pick: 1, user: 'Team Trey', fighter: 'Jon Jones', wc: 'HW' },
    ]);

    const addPick = () => {
        const newPick = {
            id: Date.now(),
            round: 2,
            pick: 1,
            user: 'Team Adan',
            fighter: 'Illia Topuria',
            wc: 'FW',
        };
        setDraftHistory([newPick, ...draftHistory]);
    };

    const removeLastPick = () => {
        // Remove the first item (newest pick)
        setDraftHistory((prev) => prev.slice(1));
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
        <ListPageLayout sx={{ mt: -6 }}> {/* Negative margin to pull columns up */}
            <Box sx={{
                mb: 3,
                p: 2,
                py: 4, // Increased vertical padding for height
                backgroundColor: 'dashboardBlack.main',
                borderRadius: 4,
            }}>
                <Grid container spacing={2}>
                    {/* 1. Timer Section */}
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
                            bgcolor: 'whiteAlpha20.main', // Darker start
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

                    {/* 3. Upcoming Picks & Round Indicator */}
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

            {/* Three-Column Layout */}
            <Grid container spacing={{ xs: .5, sm: 2 }} >
                {/* Left Column - Current Roster */}
                <Grid size={{ xs: 12, sm: 3 }}>
                    <Paper sx={{
                        height: '80vh',
                        borderRadius: 4,
                        backgroundColor: 'dashboardBlack.main',
                        p: 2, // Padding for the container
                        display: 'flex',
                        flexDirection: 'column',
                    }}>
                        {/* Header */}
                        <Box sx={{ mb: 2 }}>
                            <Typography variant="h3" sx={{ fontSize: '1rem', color: 'text.secondary' }}>Current Roster:</Typography>
                        </Box>

                        {/* ROSTER LIST LOOP - Wrapped in Stack for even spacing */}
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

                            {/* 1. TOP ROW: Info & Dropdown */}
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>

                                {/* Left Side: Avatar & Text */}
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
                                        value="all"
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
                                        <MenuItem value="all">All Weight Classes</MenuItem>
                                        <MenuItem value="hw">Heavyweight</MenuItem>
                                        <MenuItem value="lhw">Light Heavyweight</MenuItem>
                                    </Select>
                                </FormControl>
                            </Box>
                            <Box sx={{ flex: 1, overflow: 'hidden' }}>
                                <FighterTable
                                    variant="draft" // Turns on the specific Draft Board styling
                                    showStatus={false} // Hides the 'Status' column
                                />
                            </Box>
                        </Stack>
                    </Paper>
                </Grid>

                {/* Right Column - Past Picks */}
                <Grid size={{ xs: 12, sm: 3 }}>
                    <Paper sx={{
                        height: '80vh',
                        borderRadius: 4,
                        backgroundColor: 'dashboardBlack.main',
                        p: 2,
                        overflowY: 'auto'
                    }}>
                        {/* Header */}
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
