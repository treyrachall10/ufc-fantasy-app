import { DataGrid, GridColDef } from '@mui/x-data-grid';

export default function FightsList() {
    const columns: GridColDef[] = [
    { field: 'bout', headerName: 'Bout' },
    { field: 'event', headerName: 'Event' },
    { field: 'date', headerName: 'Date' },
    { field: 'winner', headerName: 'Winner' },
    ];

    const rows = [
    { id: 1, event: "UFC 322", date: "11/15/2025", bout: "Della Madalena vs. Makachev", winner: "Islam Makachev"},
    { id: 2, event: "UFC 322", date: "11/15/2025", bout: "Edwards vs. Prates", winner: "Carlos Prates"},
    ];

    return(
        <DataGrid columns={columns} rows={rows}/>
    )
}