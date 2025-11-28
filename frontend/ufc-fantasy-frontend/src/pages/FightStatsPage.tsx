import { Container, Grid } from "@mui/material";
import Sidebar from "../components/layout/Sidebar";

interface FightStatsPageProps {
    fightId: number;
}

export default function FightStatsPage({fightId}: FightStatsPageProps) {
    const FIGHTERONE = {
        name: "Alex Pereira",
        nickname: "Poatan",
        age: 36,
        height: 193, // cm
        weight: 93, // kg
        reach: 203, // cm
        stance: "Orthodox",
        w: 10,
        l: 2,
        d: 0
    };

    const FIGHTERTWO = {
        name: "Jamal Hill",
        nickname: "Sweet Dreams",
        age: 32,
        height: 193, // cm
        weight: 93, // kg
        reach: 201, // cm
        stance: "Southpaw",
        w: 12,
        l: 2,
        d: 0
    };
    return (
        <Container>
            <Grid container spacing={2}>
                {/* Fighter 1 Sidebar */}
                <Grid size={{ xs: 4, md: 2}}>
                    <Sidebar 
                        name={FIGHTERONE.name}
                        nickname={FIGHTERONE.nickname}
                        age={FIGHTERONE.age}
                        height={FIGHTERONE.height}
                        weight={FIGHTERONE.weight}
                        reach={FIGHTERONE.reach}
                        stance={FIGHTERONE.stance}
                        w={FIGHTERONE.w}
                        l={FIGHTERONE.l}
                        d={FIGHTERONE.d}
                    />
                </Grid>
                {/* Head to Head Stats */}
                <Grid size={{xs: 4, md: 8}}>
                    
                </Grid>
                {/* Fighter 2 Sidebar */}
                <Grid size={{ xs: 4, md: 2}}>
                    <Sidebar 
                        name={FIGHTERTWO.name}
                        nickname={FIGHTERTWO.nickname}
                        age={FIGHTERTWO.age}
                        height={FIGHTERTWO.height}
                        weight={FIGHTERTWO.weight}
                        reach={FIGHTERTWO.reach}
                        stance={FIGHTERTWO.stance}
                        w={FIGHTERTWO.w}
                        l={FIGHTERTWO.l}
                        d={FIGHTERTWO.d}
                    />
                </Grid>



            </Grid>
        </Container>
    )
}