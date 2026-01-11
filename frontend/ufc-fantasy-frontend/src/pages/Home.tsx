import { Container, 
        Grid, 
        Box, 
        Typography,
        Button,
        Stack,
        Card,
        CardActionArea,
        CardContent,
         } from "@mui/material";
import FlagOutlinedIcon from '@mui/icons-material/FlagOutlined';
import SportsMartialArtsOutlinedIcon from '@mui/icons-material/SportsMartialArtsOutlined';
import GitHubIcon from '@mui/icons-material/GitHub';

const cards = [
    {
        id: 1,
        icon: <FlagOutlinedIcon></FlagOutlinedIcon>,
        title: 'Leagues',
        description: 'Join or create  league'
    },
    {
        id: 2,
        icon: <SportsMartialArtsOutlinedIcon></SportsMartialArtsOutlinedIcon>,
        title: 'Fighters',
        description: 'View a list of fighters'
    },
]

const glowWrapperSx = {
  padding: '1px',
  borderRadius: '.6rem',
  position: 'relative',

  '&::before': {
    content: '""',
    position: 'absolute',
    inset: '0',
    zIndex: '0',
    background:
      'repeating-conic-gradient(from var(--a),#0f0,#ff0,#0ff,#f0f,#0ff)',
    borderRadius: '8px',
    animation: 'rotating 4s linear infinite',
  },
  '& > *': {
    position: 'relative',
    zIndex: 1,
  },
};



export default function HomePage() {
  return (
    <>
      {/* Hero */}
      <Stack direction='column' spacing={9} alignItems={'center'}>
        <Stack direction={'column'} spacing={3} alignItems={'center'}>
        <Box sx={glowWrapperSx}>
            <Button variant="contained" color="dashboardBlack" sx={{border: 'none'}} href="https://github.com/treyrachall10/ufc-fantasy-app"
            > 
            <Stack direction={'row'} gap={1} justifyContent={'center'} alignItems={'center'}>
                <GitHubIcon fontSize="medium"/>
                <Typography fontSize={'.75rem'}>STAR ON GITHUB</Typography>
            </Stack>
            </Button>
        </Box>
        {/* Hero Text */}
        <Stack spacing={1}>
            <Box sx={{display: 'flex', 
                    flexDirection: 'column',
                    alignItems: 'center', }}>
                <Typography variant='h1'>Fantasy UFC</Typography>
                <Typography variant='h1' color="brand.main">Finally season based</Typography>
            </Box>
            {/*Hero Supporting Text */}
            <Box sx={{display: 'flex', 
                    flexDirection: 'column',
                    alignItems: 'center', 
                    }}>
                <Typography variant='body' fontSize={'1.1rem'} color={'text.secondary'}>A season based fantasy league platform for UFC fans</Typography>
            </Box>
        </Stack>
        {/*Hero Buttons*/}
        <Stack direction={'row'} spacing={1} justifyContent={'center'}>
            <Button variant="contained" 
                    color='brandAlpha50' 
                    sx={{ 
                            borderColor: 'brand.light',
                            '&:hover': {
                                borderColor: 'brand.main'
                            }                        
                        }}
                >
                Join a League
            </Button>
             <Button variant="contained" color="whiteAlpha20"
                    sx={{
                        borderColor: 'gray900.main',
                        '&:hover': {
                            borderColor: 'gray800.main'
                        }
                    }}
                >
                Sign In
            </Button>
            </Stack>
        </Stack>
        {/*Hover Cards*/}
        <Stack direction={'row'} spacing={2}>
            {cards.map((card, index) => (
                <Card key={card.id} elevation={0} sx={{bgcolor: 'background.default',
                                                        borderRadius: '1rem',
                                                        }}>
                    <CardActionArea>
                        <CardContent sx={{height: '100%',
                                        bgcolor: 'background.default',
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center'
                                        }}>
                            <Stack direction={'row'} justifyContent={'center'} alignItems={'center'}>
                                {card.icon}
                                <Typography variant='subtitle2' component='div'>
                                    {card.title}
                                </Typography>
                            </Stack>
                            <Typography variant='body' component='div' color="text.secondary">
                                {card.description}
                            </Typography>
                        </CardContent>
                    </CardActionArea>
                </Card>
            ))}
        </Stack>
      </Stack>
    </>
  )
}

