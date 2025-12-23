import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Event } from '../../types/types';

export default function FightersList() {
    {/* API fetching*/}
    const { data, isPending, error } = useQuery<Event[]>({
            queryKey: ['eventListData'],
            queryFn: () => fetch('http://localhost:8000/events').then(r => r.json()),
        })
    
    if (isPending) return <span>Loading...</span>
    if (error) return <span>Oops!</span>

    const columns: GridColDef[] = [
    { field: 'event', headerName: 'Event', renderCell: (params) => (
        <Link to={`/events/${params.id}`} style={{color: "black"}}>{params.value}</Link>
    )},
    { field: 'date', headerName: 'Date' },
    { field: 'location', headerName: 'Location'}
    ];

    const rows = data.map((event) => ({
        id: event.event_id,
        event: event.event,
        location: event.location,
        date: event.date,
    }));

    return(
        <DataGrid columns={columns} rows={rows}/>
    )
}