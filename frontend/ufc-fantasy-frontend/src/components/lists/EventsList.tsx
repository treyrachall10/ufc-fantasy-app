import { DataGrid, GridColDef } from '@mui/x-data-grid';

export default function FightersList() {
    const columns: GridColDef[] = [
    { field: 'event', headerName: 'Event' },
    { field: 'date', headerName: 'Date' },
    ];

    const rows = [
    { id: 1, event: "UFC 322", date: "11/15/2025"},
    { id: 2, event: "UFC FightNight Qatar: Tsarukyan vs. Hooker", date: "11/22/2025"},
    ];

    return(
        <DataGrid columns={columns} rows={rows}/>
    )
}