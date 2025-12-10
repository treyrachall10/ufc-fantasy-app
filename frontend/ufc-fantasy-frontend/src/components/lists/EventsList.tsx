import { DataGrid, GridColDef } from '@mui/x-data-grid';

export default function FightersList() {
    const columns: GridColDef[] = [
    { field: 'event', headerName: 'Event' },
    { field: 'date', headerName: 'Date' },
    { field: 'location', headerName: 'Location'}
    ];

    const rows = [
    { id: 1, event: "UFC 322", date: "11/15/2025", location: "Location"},
    { id: 2, event: "UFC FightNight Qatar: Tsarukyan vs. Hooker", date: "11/22/2025", location: "Qatar"},
    { id: 3, event: "UFC FightNight Qatar: Tsarukyan vs. Hooker", date: "11/22/2025", location: "Qatar"},
    ];

    return(
        <DataGrid columns={columns} rows={rows}/>
    )
}