import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Link } from 'react-router-dom';
import { Fight } from '../../types/types';
import { QueryKey, useQuery } from '@tanstack/react-query';
import { useParams } from "react-router";

export default function FightsList() {
    const params = useParams()
    let queryKey: QueryKey;
    let url: string;

    if (params.id) {
        queryKey = ['fightListData', params.id];
        url = `http://localhost:8000/fights/${params.id}`;
    } else {
        queryKey = ['fightListData'];
        url = 'http://localhost:8000/fights';
    }

    {/* API fetching*/}    
    const { data, isPending, error } = useQuery<Fight[]>({
            queryKey: queryKey,
            queryFn: () => fetch(url).then(r => r.json()),
        })
    
    if (isPending) return <span>Loading...</span>
    if (error) return <span>Oops!</span>

    const columns: GridColDef[] = [
    { field: 'bout', headerName: 'Bout', renderCell: (params) => (
        <Link to={`/fighter/${params.id}`} style={{color: "black"}}>{params.value}</Link>
    )},
    { field: 'event', headerName: 'Event' },
    { field: 'weight_class', headerName: 'Weight Class' },
    { field: 'method', headerName: 'Method' },
    { field: 'round', headerName: 'Round' },
    { field: 'round_format', headerName: 'Round Format' },
    { field: 'time', headerName: 'Time' },
    { field: 'winner', headerName: 'Winner' },
    ];

    const rows = data.map((fight) => ({
        id: fight.fight_id,
        bout: fight.bout,
        event: fight.event?.event,
        weight_class: fight.weight_class,
        method: fight.method,
        round: fight.round,
        round_format: fight.round_format,
        time: fight.time,
        winner: fight.winner,
    }))

    return(
        <DataGrid columns={columns} rows={rows}/>
    )
}