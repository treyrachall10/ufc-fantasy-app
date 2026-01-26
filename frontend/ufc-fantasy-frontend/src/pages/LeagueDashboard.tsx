import * as React from 'react';
import ListPageLayout from "../components/layout/ListPageLayout";
import Avatar from '@mui/material/Avatar';
import { Box, Typography, Stack, Grid, Tooltip, ClickAwayListener, Button } from '@mui/material';
import Link from '@mui/material/Link';
import LeagueStandingsBarChart from "../components/charts/LeagueStandingsBarChart";
import LeagueStandingBarChartLabel from "../components/badges/LeagueStandingBarChartLabel";
import { DataGrid } from '@mui/x-data-grid';
import { useQuery } from "@tanstack/react-query";
import { authFetch } from "../auth/authFetch";
import { useParams } from 'react-router-dom';
import Popover from '@mui/material/Popover';
import IconButton from '@mui/material/IconButton';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import Snackbar, { SnackbarCloseReason } from '@mui/material/Snackbar';
import CloseIcon from '@mui/icons-material/Close';

interface LeagueInfo {
    league: {
        id: number
        name: string
        status: "SETUP" | "DRAFTING" | "LIVE" | "COMPLETED"
        capacity: number
        join_key: string
        created_at: string
        },
    teams: {
        id: number
        owner: number   // LeagueMember id
        name: string
        created_at: string  // ISO datetime
    }[],
}

export default function LeagueDashboard() {    

    const [open, setOpen] = React.useState(false);
    const [joinCodeAnchorEl, setJoinCodeAnchorEl] = React.useState<HTMLButtonElement | null>(null);
    const [snackbarOpen, setSnackbarOpen] = React.useState(false);
    const params = useParams();

    const { data, isPending, error} = useQuery<LeagueInfo>({
        queryKey: ['League', params.leagueId],
        queryFn: () => authFetch(`http://localhost:8000/league/${params.leagueId}`).then(r => r.json()),
    })

    if (isPending) return <span>Loading...</span>
    if (error) return <span>Oops!</span>
    
    const handleTooltipClose = () => {
        setOpen(false);
    }

    const handleTooltipOpen = () => {
        setOpen(true);
    }

    const handleJoinCodeOpen = (event: React.MouseEvent<HTMLButtonElement>) => {
        setJoinCodeAnchorEl(event.currentTarget);
    }

    const handleJoinCodeClose = () => {
        setJoinCodeAnchorEl(null);
    }



    const handleCopyClipboard = () => {
        navigator.clipboard.writeText(data?.league.join_key)
        handleSnackbarOpen();
    }

    const joinCodeOpen = Boolean(joinCodeAnchorEl);

    const handleSnackbarOpen = () => {
        setSnackbarOpen(true);
    };

    const handleSnackbarClose = (    
        event: React.SyntheticEvent | Event,
        reason?: SnackbarCloseReason,) => {
    setSnackbarOpen(false);
    };

    const action = (
        <React.Fragment>
            <IconButton
                size="small"
                aria-label="close"
                color="inherit"
                onClick={handleSnackbarClose}
            >
                <CloseIcon fontSize="small" />
            </IconButton>
        </React.Fragment>
    );

    const fantasyScoringTooltip = (
        <Typography variant="body2">
            <strong>Fantasy Scoring Breakdown</strong>
            <br /><br />
            • Knockdowns: +10 each
            <br />
            • Takedowns Landed: +3 each
            <br />
            • Submission Attempts: +2 each
            <br />
            • Control Time: +0.05 points per second
            <br /><br />
            <strong>Win & Finish Bonuses</strong>
            <br />
            • Win Bonus: +20
            <br />
            • Round 1 Finish: +30
            <br />
            • Round 2 Finish: +20
            <br />
            • Round 3–4 Finish: +10
            <br />
            • Round 5 Decision: 0
            <br /><br />
            • Early Finish Bonus: +0.03 points per second remaining in the round
        </Typography>
);

    const rowData = data.teams.map((team) => ({
        team: team.name,
        pts: 184,
        standing: 0,
        id: team.id
    }))

    const labelData = rowData.map((row) => ({
        category: row.team,
        points: row.pts,
    }))

    // Compute league standing
    for (const team of rowData) {
        let standing = 1;
        for (const comparingTeam of rowData) {
            if (team.pts < comparingTeam.pts) {
                standing +=1;
            }
        }
        team.standing = standing;
    }

    // Define the columns for the data grid
    // Each column needs: field (matches the data property name), headerName (what users see), and width
    const columns: any = [
        {field: 'standing', headerName: 'Standing', flex: .75},
        {field: 'team', headerName: 'Team', flex: 1, renderCell: (params: any) => (
            <Link 
                href={`/form/${params.value}`} 
                sx={{
                    textDecoration: 'underline',
                    color: 'text.primary'
                }}
                >{params.value}</Link>
        )},
        {field: 'pts', headerName: 'Pts', flex: .5},
    ];
    
    // Each row object must have an 'id' property and properties that match the 'field' names in columns
    // Will be replaced when API is connected. Tests out fighters with long name
    const rows = rowData.map((team, index) => ({
    id: index + 1,   // required by MUI DataGrid
    standing: team.standing,
    team: team.team,
    pts: team.pts,
    }));

    return (
        <ListPageLayout>
            <Grid
                container 
                spacing={1} 
                sx={{
                    display: 'flex',
                    justifyContent: {xs: 'center', md: 'space-between'},
                }}>
                <Grid 
                    size={{xs: 6, md: 8}}
                    sx={{
                        display: 'flex'
                    }}
                    >
                    {/* Stack formats vertical spacing between title and subtitle */}            
                    <Stack justifyContent={'space-between'}>
                        <Stack spacing={1}>
                            {/* Page title using h2 variant from theme */}
                            <Typography 
                                variant = "h2" 
                                color= "text.primary"
                                sx={{
                                    lineHeight: {xs: '1.7rem', md: '1.1rem'}
                                }}
                                > 
                                {data.league.name}
                            </Typography>
                            {/* Subtitle */}
                            <Stack direction= {{xs: "column", md: "row"}} spacing= {1} alignItems= "baseline">
                                <Typography variant= "subtitle1" color= "text.secondary">
                                    {data.league.capacity} Teams
                                </Typography>
                                <Typography variant= "body" color="text.secondary">
                                    League Owner
                                </Typography>
                            </Stack>
                            <Box>
                                <Button 
                                    variant="contained" 
                                    color='brandAlpha50'
                                    onClick={handleJoinCodeOpen}
                                    sx={{ 
                                        borderColor: 'brand.light',
                                        '&:hover': {
                                            borderColor: 'brand.main'
                                        }                        
                                    }}
                                    >
                                        Invite Friends
                                </Button>
                                <Popover
                                    open={joinCodeOpen}
                                    anchorEl={joinCodeAnchorEl}
                                    onClose={handleJoinCodeClose}
                                    anchorOrigin={{
                                        vertical: 'bottom',
                                        horizontal: 'left',
                                    }}
                                > 
                                <Stack 
                                    direction={'row'}
                                    sx={{
                                        justifyContent: 'center',
                                        alignItems: 'center',
                                        p: 1,
                                        gap: 1
                                    }}
                                >
                                    <Typography fontWeight={'600'}> Join key: </Typography>
                                        <Stack direction={'row'}>
                                        <Typography
                                            sx={{
                                                alignSelf: 'center',
                                                bgcolor: 'hsla(0, 0%, 21%, 0.50)',
                                                p: 1,
                                                borderRadius: 2
                                            }}
                                        >
                                                {data.league.join_key}
                                            </Typography>                        
                                            <IconButton
                                                onClick={handleCopyClipboard}
                                                  sx={{
                                                    '&:hover': {
                                                    backgroundColor: 'hsla(0, 91%, 43%, 0.10)',
                                                    },
                                                }}
                                                >
                                                <ContentCopyIcon
                                                fontSize='small'
                                                    sx={{
                                                        color: 'white'
                                                    }}
                                                />
                                            </IconButton>
                                        </Stack>
                                    </Stack>
                                </Popover>
                                <Snackbar
                                    open={snackbarOpen}
                                    autoHideDuration={2000}
                                    onClose={handleSnackbarClose}
                                    message="Copied to clipboard"
                                    action={action}
                                />
                            </Box>
                        </Stack>
                        <ClickAwayListener onClickAway={handleTooltipClose}>
                            <Tooltip
                                title={fantasyScoringTooltip}
                                open={open}
                                onClose={handleTooltipClose}
                                arrow={true}
                                disableFocusListener
                                disableHoverListener
                                disableTouchListener
                                slotProps={{
                                    tooltip: {
                                        sx: {
                                            maxWidth: 'none',
                                        }
                                    }
                                }}
                            >
                                <Box
                                    onClick={handleTooltipOpen}
                                    sx={{
                                        cursor: 'pointer'
                                    }}
                                >
                                    <Typography 
                                        sx={{
                                            fontSize: "1.25rem", 
                                            color: 'hsla(198, 100%, 58%, 0.5)',
                                            textDecoration: 'underline'
                                        }}>
                                        Scoring Criteria
                                    </Typography>
                                </Box>
                            </Tooltip>
                        </ClickAwayListener>
                        
                    </Stack>
                </Grid>
                {/* League Image*/}
                <Grid size={{xs: 6, sm: 4}}>
                    <Box 
                        sx={{
                            display: 'flex',
                            height: '100%',
                            justifyContent: 'center',
                            alignItems: 'center',
                        }}
                    >
                        <Avatar 
                            alt="League Image" 
                            sx={{ 
                                bgcolor: 'red',
                                height: {xs: 128, lg: 256},
                                width: {xs: 128, lg: 256}
                            }}
                            >
                            B
                        </Avatar>
                    </Box>
                </Grid>
                {/* League Standings Chart (only visible on laptop and desktop)*/}
                <Grid 
                    size={{xs: 12}}
                    sx={{
                        borderRadius: 2,
                        overflow: 'hidden',
                        position: 'relative',
                    }}
                    >
                    <Box display={{xs: 'none', md: 'block'}}>
                        <LeagueStandingsBarChart data={labelData}/>
                        {/* Custom Overlaying Chart Labels */}
                        <Box
                            sx={{
                                position: 'absolute',
                                top: 0,
                                left: 0,
                                height: '100%',
                                bgcolor: 'dashboardBlack.main',
                                pl: 3,
                                pt: 2,
                                pb: 4,
                            }}>
                                <Typography 
                                sx={{
                                    fontSize: '1rem',
                                    lineHeight: '1.3rem',
                                    letterSpacing: '0.01em',
                                    fontWeight: 500,
                                    color: 'hsla(0, 0%, 20%, 1)',
                                }}>
                                    Standings
                                </Typography>
                                <LeagueStandingBarChartLabel teams={rowData}/> {/* Creates continer of labels */}
                                </Box>
                    </Box>
                        {/* League Standings List (only visible on mobile and tablet)*/}
                        <Box sx={{ 
                                width: '100%', 
                                overflow: "hidden", 
                                display: {xs: 'block', md: 'none'},
                                }}>
                            <DataGrid //displays the table 
                                rows= {rows} 
                                columns= {columns} 
                                hideFooter 
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
                    
                                })}      
                            />
                        </Box>
                </Grid>
            </Grid>
        </ListPageLayout>
    )
}