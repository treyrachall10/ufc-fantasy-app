import ListPageLayout from "../components/ListPageLayout";
import ListHeader from "../components/ListHeader";
import FightersList from "../components/FightersList"

export default function FightersListPage() {
    return (
        <ListPageLayout>
            <ListHeader title="Fighters" searchBarLabel="Search by fighter name"></ListHeader>
            <FightersList></FightersList>
        </ListPageLayout>
    )
}