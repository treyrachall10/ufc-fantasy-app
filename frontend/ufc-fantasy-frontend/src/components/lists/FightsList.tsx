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
    { id: 3, event: "UFC 323", date: "12/07/2025", bout: "Holloway vs. Topuria", winner: "Ilia Topuria"},
    { id: 4, event: "UFC 323", date: "12/07/2025", bout: "Whittaker vs. Cannonier", winner: "Robert Whittaker"},
    { id: 5, event: "UFC 324", date: "01/18/2026", bout: "O’Malley vs. Vera", winner: "Sean O’Malley"},
    ];

    return(
        <DataGrid columns={columns} rows={rows}/>
    )
}