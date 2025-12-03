import { Container, Grid, Box} from "@mui/material";
import Sidebar from "../components/layout/Sidebar";
import DivergingProgressBar from "../components/statHolders/DivergingProgressBar";
import HeadToHeadStatCard from "../components/statHolders/HeadToHeadStatCard";

interface FightStatsPageProps {
    fightId: number;
}

export default function FightStatsPage({fightId}: FightStatsPageProps) {
    const fighterOne = {
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

    const fighterTwo = {
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
        <Container maxWidth='xl'>
            <Grid container spacing={2}>
                {/* Fighter 1 Sidebar */}
                <Grid size={{ xs: 4, md: 2}}>
                    <Sidebar 
                        name={fighterOne.name}
                        nickname={fighterOne.nickname}
                        age={fighterOne.age}
                        height={fighterOne.height}
                        weight={fighterOne.weight}
                        reach={fighterOne.reach}
                        stance={fighterOne.stance}
                        w={fighterOne.w}
                        l={fighterOne.l}
                        d={fighterOne.d}
                    />
                </Grid>
                {/* Head to Head Stats */}
                <Grid size={{xs: 4, md: 8}} spacing={2}>
                    <Box sx={{
                        display:'flex',
                        flexDirection: 'column',
                        gap: 1
                        }}>
                    <HeadToHeadStatCard title={"Strike Accuracy"} leftValue={fighterOne.w} rightValue={fighterTwo.w}/>
                    <HeadToHeadStatCard title={"Strike Accuracy"} leftValue={fighterOne.w} rightValue={fighterTwo.w}/>
                    <HeadToHeadStatCard title={"Strike Accuracy"} leftValue={fighterOne.w} rightValue={fighterTwo.w}/>
                    <HeadToHeadStatCard title={"Strike Accuracy"} leftValue={fighterOne.w} rightValue={fighterTwo.w}/>
                    </Box>
                </Grid>
                {/* Fighter 2 Sidebar */}
                <Grid size={{ xs: 4, md: 2}}>
                    <Sidebar 
                        name={fighterTwo.name}
                        nickname={fighterTwo.nickname}
                        age={fighterTwo.age}
                        height={fighterTwo.height}
                        weight={fighterTwo.weight}
                        reach={fighterTwo.reach}
                        stance={fighterTwo.stance}
                        w={fighterTwo.w}
                        l={fighterTwo.l}
                        d={fighterTwo.d}
                    />
                </Grid>


            </Grid>
        </Container>
    )
}