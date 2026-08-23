import * as React from 'react';
import ListPageLayout from "../components/layout/ListPageLayout";
import { Box, Typography, Stack, Grid, Tooltip, ClickAwayListener, Button } from '@mui/material';
import Link from '@mui/material/Link';
import LeagueStandingsBarChart from "../components/charts/LeagueStandingsBarChart";
import LeagueStandingBarChartLabel from "../components/badges/LeagueStandingBarChartLabel";
import { DataGrid } from '@mui/x-data-grid';
import { useQuery } from "@tanstack/react-query";
import { useAuthFetch } from "../auth/authFetch";
import { getApiBaseUrl } from "../config/api";
import { useParams } from 'react-router-dom';
import Popover from '@mui/material/Popover';
import IconButton from '@mui/material/IconButton';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import Snackbar, { SnackbarCloseReason } from '@mui/material/Snackbar';
import CloseIcon from '@mui/icons-material/Close';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import type { Dayjs } from 'dayjs';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'
import timezone from 'dayjs/plugin/timezone'
import { Link as RouterLink } from 'react-router-dom';
import { LeagueInfo } from '../types/types';
import { useCurrentUser } from '../auth/useCurrentUser';

dayjs.extend(utc);
dayjs.extend(timezone);

interface SetDraftSatePayload {
    draft_date: string,
}

export default function LeagueDashboard() {   
    const params = useParams();
    const authFetch = useAuthFetch();
    const queryClient = useQueryClient();
    const { data: user, isLoading: userLoading } = useCurrentUser()

    const [open, setOpen] = React.useState(false);
    const [draftDate, setDraftDate] = React.useState<Dayjs | null>(null);
    const [draftDateError, setDraftDateError] = React.useState<string>("");
    const [joinCodeAnchorEl, setJoinCodeAnchorEl] = React.useState<HTMLButtonElement | null>(null);
    const [snackbarOpen, setSnackbarOpen] = React.useState(false);

    const { data, isPending, error} = useQuery<LeagueInfo>({
        queryKey: ['League', params.leagueId],
        queryFn: () => authFetch(`${getApiBaseUrl()}/league/${params.leagueId}`).then(r => r.json()),
    })

    const scheduleDraftMutation = useMutation({
        mutationFn: async (payload: SetDraftSatePayload) => {
        const response = await authFetch(`${getApiBaseUrl()}/league/${params.leagueId}/draft/schedule`, {
            method: 'POST',
            body: JSON.stringify(payload),
        })
    
        const data = await response.json()
    
        if (!response.ok) {
            throw data
        }
    
        return data
        },

        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['League'] });
            setDraftDateError("");
        },
        onError: (error: any) => {
            const errorMessage = error?.detail || "An error occurred scheduling the draft";
            setDraftDateError(errorMessage);
        }
    })

    if (isPending || userLoading) return <span>Loading...</span>
    if (error) return <span>Oops!</span>

    const isCreator = user?.user.id === data.league.creator;
    const teams = data.teams.length; // Number of teams in league
    const capacity = data.league.capacity; // Max capacity for league
    const isLeagueOpen = capacity > 0
    const missing = capacity - teams; // Number of teams left to reach max capacity
    const draftStatus = data.draft.status

    const canScheduleDraft = isCreator && draftStatus === "NOT_SCHEDULED";
    const isDraftScheduled = draftStatus === "PENDING";
    const nonCreatorDraftNotScheduled = !isCreator && draftStatus === "NOT_SCHEDULED";
    const isDraftInProgress = draftStatus === "IN_PROGRESS";

    const handleTooltipClose = () => {
        setOpen(false);
    }

    const handleTooltipOpen = () => {
        setOpen(true);
    }

    const isInvalidDraftDate = !!draftDate && draftDate.isBefore(dayjs());

    const shouldDisableDate = (date: Dayjs | null) => {
        if (!date) return false;
        const chicagoTime = date.utc().tz('America/Chicago');
        return chicagoTime.day() === 6; // Saturday is disabled
    };

    const shouldDisableTime = (value: Dayjs, view: string) => {
        const chicagoTime = value.utc().tz('America/Chicago');
        const isSunday = chicagoTime.day() === 0;
        const hour = chicagoTime.hour();
        return isSunday && (hour === 0 || hour === 1); // Disable 12AM-2AM on Sundays
    };

    const handleDraftDateAccept = (date: Dayjs | null) => {
        if (!date || date.isBefore(dayjs())) return;
        scheduleDraftMutation.mutate({
            draft_date: date.utc().toISOString(),
        });
    };

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

const scheduleDraftSection = (
    <Stack spacing={0.5}>
        <LocalizationProvider dateAdapter={AdapterDayjs}>
            <DateTimePicker
                label="Select Draft Date & Time"
                value={draftDate}
                onChange={(date) => {
                    setDraftDate(date);
                    setDraftDateError("");
                }}
                onAccept={handleDraftDateAccept}
                disablePast={true}
                shouldDisableDate={shouldDisableDate}
                shouldDisableTime={shouldDisableTime}
                disabled={missing > 0}
                desktopModeMediaQuery="@media (min-width:0px)"
                sx={{
                    margin: 1,
                }}
                slotProps={{
                    actionBar: {
                        actions: ['cancel', 'accept'],
                    },
                    textField: {
                        className: `league-draft-picker ${missing === 0 ? 'league-draft-picker--full' : ''}`,
                        size: 'small',
                        error: Boolean(isInvalidDraftDate || draftDateError),
                        helperText: draftDateError || (isInvalidDraftDate ? "Date must be in the future" : ""),
                        sx: {
                            width: 'fit-content',
                            '& .MuiInputLabel-root': {
                                color: 'text.secondary',
                                whiteSpace: 'nowrap',
                            },
                            '& .MuiInputBase-input': {
                                color: 'text.primary',
                            },
                            '& .MuiSvgIcon-root': {
                                color: 'text.primary',
                            },
                        },
                    },
                }}
            />
        </LocalizationProvider>
        {missing > 0 && (
        <Typography fontSize="0.75rem" color="text.secondary" alignSelf={'center'}>
            Waiting for {missing} more teams
        </Typography>
        )}
    </Stack>
)

const DraftScheduled = () => {
    return (
        <Stack spacing={0.5}>
            <Button
                variant="contained"
                color="whiteAlpha20"
                component={RouterLink} to={`/league/${data.league.id}/draft/${data.draft.id}`}
                sx={{
                    borderColor: 'gray900.main',
                    '&:hover': {
                        borderColor: 'gray800.main'
                    },
                    '&.Mui-disabled': {
                        backgroundColor: 'hsla(0, 0%, 21%, 0.20)',
                        color: 'text.secondary',
                        borderColor: 'gray800.main',
                    },
                }}
            >
            Enter Draft Room
            </Button>
            <Typography fontSize="0.75rem" color="text.secondary" alignSelf={'center'}>
                Draft is set for {dayjs(data.draft.draft_date).format("MMM D, YYYY h:mm A")}
            </Typography>
        </Stack>
    )
}

const NonCreatorDraftNotScheduled = () => {
    return (
        <Typography fontSize="0.75rem" color="text.secondary" alignSelf={'center'}>
            Draft has not yet been scheduled
        </Typography>
    )
}

    const rowData = data.teams.map((team) => ({
        team: team.name,
        pts: parseFloat(team.score?.toFixed(2) ?? '0'),
        standing: 0,
        id: team.id,
        img_url: team.img_url ?? null,
    }))

    const labelData = rowData.map((row) => ({
        category: row.team,
        points: row.pts,
        img_url: row.img_url
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
                href={`/team/${params.id}`} 
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
    id: team.id,
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
                    size={{xs: 12, md: 12}}
                    sx={{
                        display: 'flex',
                        width: '100%'
                    }}
                    >
                    <Stack
                        direction={{ xs: 'column', md: 'row' }}
                        justifyContent={'space-between'}
                        sx={{
                            width: '100%',
                            gap: 2,
                        }}
                    >
                        {/* Stack formats vertical spacing between title and subtitle */}
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
                            <Stack direction={'row'} gap={1} alignItems={'flex-start'}>
                                {isLeagueOpen && (
                                <>
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
                                </>
                            )}
                                {canScheduleDraft && scheduleDraftSection}
                                {(isDraftScheduled || isDraftInProgress) && <DraftScheduled/>}
                                {nonCreatorDraftNotScheduled && <NonCreatorDraftNotScheduled/>}
                                <Snackbar
                                    open={snackbarOpen}
                                    autoHideDuration={2000}
                                    onClose={handleSnackbarClose}
                                    message="Copied to clipboard"
                                    action={action}
                                />
                            </Stack>
                        </Stack>
                        <Box
                            sx={{
                                display: 'flex',
                                alignItems: { xs: 'flex-end', md: 'flex-end' },
                                justifyContent: { xs: 'flex-end', md: 'flex-end' },
                            }}
                        >
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
                        </Box>
                    </Stack>
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