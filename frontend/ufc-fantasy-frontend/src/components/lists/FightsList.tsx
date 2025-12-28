import { DataGrid, GridColDef } from '@mui/x-data-grid';
import { Link } from 'react-router-dom';
import { Fight } from '../../types/types';
import { QueryKey, useQuery } from '@tanstack/react-query';
import { useParams, useLocation } from "react-router";

export default function FightsList() {
    const params = useParams()
    const location = useLocation()
    
    let queryKey: QueryKey;
    let url: string;

    const isFighterPage = location.pathname.startsWith("/fighter");
    const isEventPage = location.pathname.startsWith("/events");
    const isFightsPage = location.pathname.startsWith("/fights");

    if (isFighterPage && params.id) {
        queryKey = ['fightListDataWithId', params.id];
        url = `http://localhost:8000/fights/${params.id}`;
    } else if (isFightsPage) {
        queryKey = ['fightListData'];
        url = 'http://localhost:8000/fights';
    } else if (isEventPage) {
        queryKey = ['eventFightsListdata', params.id];
        url = `http://localhost:8000/events/${params.id}`;
    } else {
        queryKey = ["/"];
        url = ""
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
        <Link to={`/fight/${params.id}`} style={{color: "black"}}>{params.value}</Link>
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
    
    const compactInitialState = {
        pagination: {
          paginationModel: {
            pageSize: 5,
          },
        },
      };
    
    if (location.pathname.includes("fighter")) {
       return(
            <DataGrid 
                columns={columns} 
                rows={rows} 
                initialState={compactInitialState}
            />
        );
    } else { 
        return (
            <DataGrid columns={columns} rows={rows} />
        );
    }
    
}