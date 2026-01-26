import Box from "@mui/material/Box"
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Avatar from '@mui/material/Avatar';
import { Link } from "react-router-dom";

interface TeamStanding {
  team: string;
  pts: number;
  standing: number;
  id: number;
}

interface LeagueStandingBarChartLabelProps {
  teams: TeamStanding[];
}

const ROW_HEIGHT = 48;

export default function LeagueStandingBarChartLabel({ teams }: LeagueStandingBarChartLabelProps) {
    // Turn league standings numbers to string
    const labels = teams.map(team => {
        if (team.standing === 1) return '1st Place';
        if (team.standing === 2) return '2nd Place';
        if (team.standing === 3) return '3rd Place';
        return `${team.standing}th Place`;
    });

  return (
    <Stack height={'100%'} justifyContent={'space-around'}
        sx={{
            height: '100%',
            justifyContent: 'space-around',
            pt: 2,
        }}
    >
      {teams.map((team, i) => (
        <Box
          key={team.team}
          sx={{
            height: ROW_HEIGHT,
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Stack direction="row" spacing={1} >
            {/* Avatar */}
            <Box sx={{ display: 'flex'}}>
              <Avatar
                alt="League Image"
                sx={{
                  height: '64px',
                  width: '64px',
                  bgcolor: 'lightBlue',
                }}
              >
                B
              </Avatar>
            </Box>

            {/* Text */}
            <Stack direction="column" spacing={0.5} justifyContent="center">
              <Typography variant="subtitle2" lineHeight="1rem">
                {team.team}
              </Typography>

              <Stack direction="row" spacing={0.5} alignItems="center">
                <Typography color="text.secondary" lineHeight="1rem">
                  {labels[i]}
                </Typography>

                <Button
                  variant="contained"
                  color="whiteAlpha20"
                  size="small"
                  component={Link} to={`/team/${team.id}`}
                  sx={{
                    fontSize: '0.75rem',
                    fontWeight: 400,
                    padding: '2px 4px',
                    lineHeight: '1rem',
                    borderColor: 'gray900.main',
                    '&:hover': {
                      borderColor: 'gray800.main',
                    },
                  }}
                >
                  View Roster
                </Button>
              </Stack>
            </Stack>
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}