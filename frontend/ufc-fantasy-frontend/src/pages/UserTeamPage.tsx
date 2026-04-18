import ListPageLayout from "../components/layout/ListPageLayout";
import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Avatar, Box, Typography, Stack, IconButton, Tooltip } from '@mui/material';
import { Link, useParams } from "react-router-dom";
import { useAuthFetch } from "../auth/authFetch";
import { useQuery } from "@tanstack/react-query";
import { TeamDataResponse } from "../types/types";
import SettingsRoundedIcon from '@mui/icons-material/SettingsRounded';
import { useCurrentUser } from "../auth/useCurrentUser";

export default function UserTeamPage() {
    const authFetch = useAuthFetch();
    const params = useParams();
    const { data: currentUser } = useCurrentUser();

    const { data, isPending, error} = useQuery<TeamDataResponse>({
        queryKey: ['Team', params.teamid],
        queryFn: () => authFetch(`http://localhost:8000/team/${params.teamid}`).then(r => r.json()),
    })

    if (isPending) return <span>Loading...</span>
    if (error) return <span>Oops!</span>

    const isOwnerViewingTeam =
        currentUser?.user.username === data.team.owner;

    // Define the columns for the data grid
    // Each column needs: field (matches the data property name), headerName (what users see), and width
    const columns: GridColDef[] = [
        {field: 'weightClass', headerName: 'Weight Class', flex: 1, minWidth: 120},
            {
        field: 'fighter',
        headerName: 'Fighter',
        flex: 2,
        renderCell: (params) => (
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                <Avatar src={params.row.img_url || undefined} alt={params.value} sx={{ marginRight: 1 }} />
                <Link to={`/fighter/${params.id}`} style={{ color: 'white' }}>
                    {params.value}
                </Link>
            </Box>
        ),
    }, //Flex keeps consistent sizing when chaning window size
        {field: 'status', headerName: 'Status', flex: 1.0, minWidth: 120},
        {field: 'projected', headerName: 'Projected', flex: 0.7, minWidth: 110},
        {field: 'year', headerName: 'Year', flex: 0.7, minWidth: 90},
        {field: 'average', headerName: 'Avg', flex: 0.6, minWidth: 80},
        {field: 'last', headerName: 'Last', flex: 1, minWidth: 80}
    ];
    
    // Each row object must have an 'id' property and properties that match the 'field' names in columns
    // Will be replaced when API is connected. Tests out fighters with long name

    const rows = data.roster.map((slot, index) => ({
        id: slot.fighter?.fighter_id || index,
        weightClass: slot.slot,
        fighter: slot.fighter?.full_name || 'Empty',
        status: 'Coming Soon',
        projected: 'Coming Soon',
        year: slot.fantasy?.total_points_since_draft,
        average: slot.fantasy ? slot.fantasy.average_points.toFixed(1) : '0.0',
        last: slot.fantasy ? slot.fantasy.last_fight_points.toFixed(1) : '0.0',
        img_url: slot.fighter?.img_url || null,
    }))
    
    return (
        <ListPageLayout>

            <Box sx={{ width: '100%' }}>

            {/* Stack formats vertical spacing between title and subtitle */}            
            <Stack spacing={2} sx={{ mb: 3, width: '100%' }}>
                <Stack direction="row" justifyContent="space-between" alignItems="flex-start" sx={{ width: '100%' }}>
                    <Stack spacing={1} alignItems="flex-start" sx={{ textAlign: 'left' }}>
                        <Typography variant="h2" color="text.primary">
                            {data.team.name}
                        </Typography>
                        <Stack direction="row" spacing={1} alignItems="baseline">
                            <Typography variant="subtitle1" color="text.secondary">
                                {data.team.score} pts
                            </Typography>
                            <Typography variant="body" color="text.secondary">
                                {data.team.owner}
                            </Typography>
                        </Stack>
                    </Stack>

                    <Stack direction="row" spacing={1} alignItems="flex-end">
                        <Avatar
                            src={data.team.img_url || undefined}
                            alt={`${data.team.name} avatar`}
                            sx={{
                                height: { xs: 128, lg: 256 },
                                width: { xs: 128, lg: 256 },
                            }}
                        />
                        {isOwnerViewingTeam && (
                            <Tooltip title="Edit Team Settings" placement="left">
                                <IconButton
                                    component={Link}
                                    to={`/team/${params.teamid}/settings`}
                                    aria-label="Edit team settings"
                                    size="large"
                                    sx={{
                                        color: 'text.secondary',
                                        alignSelf: 'flex-end',
                                        '&:hover': {
                                            color: 'text.primary',
                                            backgroundColor: 'transparent',
                                        },
                                    }}
                                >
                                    <SettingsRoundedIcon />
                                </IconButton>
                            </Tooltip>
                        )}
                    </Stack>
                </Stack>
            </Stack>
            <Box sx={{ width: '100%', overflow: "hidden" }}>
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
            </Box>
        </ListPageLayout>
    )
}
