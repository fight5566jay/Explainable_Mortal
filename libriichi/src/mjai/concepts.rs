use crate::{algo::shanten, hand::tiles_to_string, state::PlayerState, tile::Tile};
use pyo3::prelude::*;
use serde::{Deserialize, Serialize};
use serde_big_array::BigArray;
use serde_with::skip_serializing_none;

#[skip_serializing_none]
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass(dict, get_all, set_all)]
pub struct Concepts {
    //[TODO] print tehai as string array like ["2m", "2m", "3m", ...]
    #[serde(with = "BigArray")]
    pub tehai: [u8; 34], // Basic test for vector value

    pub doras_owned: u8,
    pub shanten: i8,
    pub suit_count: i8,
    pub is_one_chance: [bool; 27],
    pub current_rank: u8,

    //[TODO] print next_shanten_tsumo as string array like ["1m", "2m", "4m", ...]
    #[serde(with = "BigArray")]
    pub next_shanten_tsumo_normal: [bool; 34],

    #[serde(with = "BigArray")]
    pub solitary_tiles: [bool; 34],

    pub is_suji: [[bool; 27]; 3], //From 1 to 9 of manzu, pinzu, souzu. True if the tile is suji tile.
}

/*
const fn default_opponent_tehais() -> [[u8; 34]; 3] {
    [[0_u8; 34]; 3]
}
*/

impl Default for Concepts {
    fn default() -> Self {
        Self {
            tehai: [0_u8; 34],
            doras_owned: 0,
            shanten: 0,
            suit_count: 0,
            is_one_chance: [false; 27],
            current_rank: 0,
            next_shanten_tsumo_normal: [false; 34],
            solitary_tiles: [false; 34],
            is_suji: [[false; 27]; 3],
        }
    }
}

#[pymethods]
impl Concepts {
    #[new]
    #[allow(clippy::too_many_arguments)]
    const fn new(
        tehai: [u8; 34],
        doras_owned: u8,
        shanten: i8,
        suit_count: i8,
        is_one_chance: [bool; 27],
        current_rank: u8,
        next_shanten_tsumo_normal: [bool; 34],
        solitary_tiles: [bool; 34],
        is_suji: [[bool; 27]; 3],
    ) -> Self {
        Self {
            tehai,
            doras_owned,
            shanten,
            suit_count,
            is_one_chance,
            current_rank,
            next_shanten_tsumo_normal,
            solitary_tiles,
            is_suji,
        }
    }

    /// Convert to a Python dictionary
    fn to_dict<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, pyo3::types::PyDict>> {
        let dict = pyo3::types::PyDict::new(py);

        // Convert tehai to Python list of integers
        let tehai_list = pyo3::types::PyList::new(py, self.tehai.iter().map(|&x| x as i32))?;
        dict.set_item("tehai", tehai_list)?;

        dict.set_item("doras_owned", self.doras_owned)?;
        dict.set_item("shanten", self.shanten)?;
        dict.set_item("suit_count", self.suit_count)?;

        let is_one_chance_list = pyo3::types::PyList::new(py, self.is_one_chance.iter().copied())?;
        dict.set_item("is_one_chance", is_one_chance_list)?;

        dict.set_item("current_rank", self.current_rank)?;

        // Convert next_shanten_tsumo to Python list of booleans
        let next_shanten_tsumo_list =
            pyo3::types::PyList::new(py, self.next_shanten_tsumo_normal.iter().copied())?;
        dict.set_item("next_shanten_tsumo_normal", next_shanten_tsumo_list)?;

        // Convert solitary_tiles to Python list of booleans
        let solitary_tiles_list =
            pyo3::types::PyList::new(py, self.solitary_tiles.iter().copied())?;
        dict.set_item("solitary_tiles", solitary_tiles_list)?;

        // Convert is_suji to Python nested list: 3*[bool; 27]
        for (i, opponent_suji) in self.is_suji.iter().enumerate() {
            let opponent_suji_list = pyo3::types::PyList::new(py, opponent_suji.iter().copied())?;
            dict.set_item(format!("is_suji_opponent_{i}"), opponent_suji_list)?;
        }

        Ok(dict)
    }
}

impl Concepts {
    /// Generate Concepts from PlayerState
    #[inline]
    #[must_use]
    pub fn from_player_state(state: &PlayerState) -> Self {
        let tehai = state.tehai();

        let shanten = shanten::calc_all(&tehai, state.tehai_len_div3()); //Do use state.shanten here because it is calculated before tsumo.

        let mut suit_count = 0;

        //manzu, pinzu, souzu
        for suit in 0..3 {
            for rank in 1..=9 {
                let tile_u8 = suit * 9 + (rank - 1);
                if tehai[tile_u8 as usize] > 0 {
                    suit_count += 1;
                    /*if suit == 0 {
                        have_manzu = true;
                    }*/
                    break;
                }
            }
        }
        //jihai
        for tile_u8 in 27..34 {
            if tehai[tile_u8 as usize] > 0 {
                suit_count += 1;
                break;
            }
        }

        // No chance
        let tile_seen = state.tiles_seen();
        let is_one_chance: [bool; 27] = core::array::from_fn(|i| {
            let tile = Tile::try_from(i as u8).unwrap();
            Self::is_the_tile_one_chance(tile, &tile_seen)
        });

        //Current rank
        let scores = state.scores();
        let mut current_rank = 0;
        for &score in &scores {
            if score >= scores[0] {
                current_rank += 1;
            }
        }

        let next_shanten_tsumo_normal = Self::calc_next_shanten_tsumo_normal(
            &tehai,
            state.tehai_len_div3(),
            state.last_cans().can_agari(),
        );
        let solitary_tiles = Self::calc_solitary_tiles(&tehai);
        let is_suji = Self::calc_suji(state);

        Self {
            tehai,
            doras_owned: state.doras_owned()[0],
            shanten,
            suit_count,
            is_one_chance,
            current_rank,
            next_shanten_tsumo_normal,
            solitary_tiles,
            is_suji,
        }
    }

    /// Calculate suji for each of the 3 opponents
    /// A tile is suji if opponents cannot ron it with ryanmen due to furiten
    /// [TODO] Add same round furiten
    #[inline]
    #[must_use]
    fn calc_suji(state: &PlayerState) -> [[bool; 27]; 3] {
        let mut is_suji = [[false; 27]; 3];

        let riichi_accepted = state.riichi_accepted();
        let kawa = state.kawa();
        let kawa_overview = state.kawa_overview();

        // For each opponent (relative positions 1, 2, 3)
        for opponent_rel in 1..4 {
            let opponent_idx = opponent_rel - 1;

            // For each suited tile (27 tiles, excluding jihai)
            for tile_id in 0..27 {
                let tile = Tile::try_from(tile_id as u8).unwrap();
                let rank = (tile.as_u8() % 9) + 1; // 1-9

                // Ryanmen pairs: (1,4), (2,5), (3,6), (4,7), (5,8), (6,9)
                // For tiles 4/5/6, they need BOTH partners discarded to be suji
                let suji_partners: [Option<usize>; 2] = [
                    if rank >= 4 { Some(tile_id - 3) } else { None }, // rank - 3
                    if rank <= 6 { Some(tile_id + 3) } else { None }, // rank + 3
                ];

                let has_both_partners = suji_partners[0].is_some() && suji_partners[1].is_some();

                // Type 1: Discarded furiten suji
                // Check if opponent has discarded the partner(s)
                let mut partner0_discarded_by_opponent = false;
                let mut partner1_discarded_by_opponent = false;

                if let Some(pid) = suji_partners[0] {
                    let partner_tile = Tile::try_from(pid as u8).unwrap();
                    partner0_discarded_by_opponent =
                        kawa_overview[opponent_rel].contains(&partner_tile);
                }
                if let Some(pid) = suji_partners[1] {
                    let partner_tile = Tile::try_from(pid as u8).unwrap();
                    partner1_discarded_by_opponent =
                        kawa_overview[opponent_rel].contains(&partner_tile);
                }

                // Type 3: Riichi furiten suji
                // Check if tiles were discarded by OTHER opponents AFTER this opponent's riichi was accepted
                let mut partner0_discarded_after_riichi = false;
                let mut partner1_discarded_after_riichi = false;

                if riichi_accepted[opponent_rel] {
                    // Find the position (game round index) where opponent declared riichi
                    // Use the kawa field which maintains synchronized indices across all players
                    let riichi_round_idx = kawa[opponent_rel].iter().position(|item| {
                        item.as_ref()
                            .is_some_and(|kawa_item| kawa_item.sutehai().is_riichi())
                    });

                    if let Some(riichi_idx) = riichi_round_idx {
                        // Check other opponents' discards AFTER the riichi (after this round index or after riichi in this round)
                        for (other_rel, other_kawa) in kawa.iter().enumerate().skip(1).take(3) {
                            if other_rel == opponent_rel {
                                continue;
                            }
                            let kawa_after_riichi_start_idx = if other_rel < opponent_rel {
                                riichi_idx + 1
                            } else {
                                riichi_idx
                            };

                            // Check partner 0
                            if let Some(pid) = suji_partners[0] {
                                let partner_tile = Tile::try_from(pid as u8).unwrap();
                                // Check tiles discarded after riichi round in the same game timeline
                                for kawa_item in other_kawa
                                    .iter()
                                    .skip(kawa_after_riichi_start_idx)
                                    .flatten()
                                {
                                    if kawa_item.sutehai().tile().deaka() == partner_tile.deaka() {
                                        partner0_discarded_after_riichi = true;
                                        break;
                                    }
                                }
                            }

                            // Check partner 1
                            if let Some(pid) = suji_partners[1] {
                                let partner_tile = Tile::try_from(pid as u8).unwrap();
                                for kawa_item in other_kawa
                                    .iter()
                                    .skip(kawa_after_riichi_start_idx)
                                    .flatten()
                                {
                                    if kawa_item.sutehai().tile().deaka() == partner_tile.deaka() {
                                        partner1_discarded_after_riichi = true;
                                        break;
                                    }
                                }
                            }
                        }
                    }
                }

                // Combine Type 1 (Discarded furiten) and Type 3 (Riichi furiten)
                // For 4/5/6: need BOTH partners (either from discarded furiten OR riichi furiten)
                // For 1/2/3/7/8/9: need the ONE partner
                if has_both_partners {
                    let partner0_suji =
                        partner0_discarded_by_opponent || partner0_discarded_after_riichi;
                    let partner1_suji =
                        partner1_discarded_by_opponent || partner1_discarded_after_riichi;
                    if partner0_suji && partner1_suji {
                        is_suji[opponent_idx][tile_id] = true;
                    }
                } else {
                    // Only one partner exists
                    if (suji_partners[0].is_some()
                        && (partner0_discarded_by_opponent || partner0_discarded_after_riichi))
                        || (suji_partners[1].is_some()
                            && (partner1_discarded_by_opponent || partner1_discarded_after_riichi))
                    {
                        is_suji[opponent_idx][tile_id] = true;
                    }
                }
            }
        }

        is_suji
    }

    #[inline]
    #[must_use]
    const fn is_the_tile_one_chance(tile: Tile, tile_seen: &[u8; 34]) -> bool {
        //let tile_kind = tile.as_u8() / 9;
        let tile_rank = (tile.as_u8() % 9 + 1) as usize;
        if tile_rank > 3 && tile_seen[tile_rank - 2] < 3 && tile_seen[tile_rank - 1] < 3 {
            // can wait tile and tile - 3
            return false;
        }
        if tile_rank < 7 && tile_seen[tile_rank + 1] < 3 && tile_seen[tile_rank + 2] < 3 {
            // can wait tile and tile + 3
            return false;
        }

        true
    }

    #[inline]
    #[must_use]
    fn calc_next_shanten_tsumo_normal(
        tehai: &[u8; 34],
        tehai_len_div3: u8,
        can_agari: bool,
    ) -> [bool; 34] {
        //Next shanten tsumo
        let mut next_shanten_tsumo_normal = [false; 34];
        let shanten_normal = shanten::calc_normal(tehai, tehai_len_div3); //Do use state.shanten here because it is calculated before tsumo.

        if can_agari && shanten_normal == -1 {
            //If can agari with normal winning form, no need to calculate next shanten tsumo
            return [false; 34];
        }

        if tehai.iter().sum::<u8>() % 3 == 1 {
            //3n+1 case
            let mut tehai_clone = *tehai;
            for tsumo_tile in 0..34 {
                if next_shanten_tsumo_normal[tsumo_tile] || tehai_clone[tsumo_tile] >= 4 {
                    continue;
                }
                tehai_clone[tsumo_tile] += 1;
                let new_shanten = shanten::calc_normal(&tehai_clone, tehai_len_div3);
                //println!("Debug: tsumo_tile={tsumo_tile}, new_shanten={new_shanten}, current_shanten={current_shanten}");
                assert!(new_shanten <= shanten_normal);
                next_shanten_tsumo_normal[tsumo_tile] = new_shanten < shanten_normal;
                tehai_clone[tsumo_tile] -= 1;
            }
        } else if tehai.iter().sum::<u8>() % 3 == 2 {
            //3n+2 case
            //[TODO] Steel have bug. Currently (but it shouldn't be) always all false.
            let mut tehai_clone = *tehai;

            //Discard next shanten tile first
            for discarded_tile in 0..34 {
                if tehai_clone[discarded_tile] == 0 {
                    continue;
                }
                tehai_clone[discarded_tile] -= 1;
                let new_discard_shanten = shanten::calc_normal(&tehai_clone, tehai_len_div3);
                /*
                println!(
                    "Debug: tehai_clone={}",
                    tiles_to_string(&tehai_clone, [false; 3])
                );
                println!("discarded_tile={discarded_tile}");
                println!("new_discard_shanten={new_discard_shanten}, shanten={shanten}");
                */
                if new_discard_shanten > shanten_normal {
                    tehai_clone[discarded_tile] += 1;
                    continue;
                }

                //calculate next shanten tsumo after discard
                for tsumo_tile in 0..34 {
                    if next_shanten_tsumo_normal[tsumo_tile] || tehai_clone[tsumo_tile] >= 4 {
                        continue;
                    }
                    tehai_clone[tsumo_tile] += 1;
                    let new_tsumo_shanten = shanten::calc_normal(&tehai_clone, tehai_len_div3);
                    /*
                    println!(
                        "Debug: tehai_clone={}",
                        tiles_to_string(&tehai_clone, [false; 3])
                    );
                    println!("tsumo_tile={tsumo_tile}");
                    println!("new_shanten={new_tsumo_shanten}, shanten={shanten}");
                    let nst = new_tsumo_shanten < shanten;
                    println!("nst={nst}");
                    */
                    assert!(new_tsumo_shanten <= shanten_normal);
                    next_shanten_tsumo_normal[tsumo_tile] = new_tsumo_shanten < shanten_normal;
                    tehai_clone[tsumo_tile] -= 1;
                }

                tehai_clone[discarded_tile] += 1;
                //println!("Debug: tehai_clone={tehai_clone:?}, tehai={tehai:?}");
                assert_eq!(tehai_clone, *tehai);
            }
        }

        //Use assertion to check
        //It should be at least one possible next shanten tsumo if shanten > -1
        if shanten_normal > -1 {
            assert!(
                next_shanten_tsumo_normal.iter().any(|&x| x),
                "No possible next shanten tsumo found in tehai {} when shanten = {shanten_normal}",
                tiles_to_string(tehai, [false; 3])
            );
        }
        next_shanten_tsumo_normal
    }

    #[inline]
    #[must_use]
    fn calc_solitary_tiles(tehai: &[u8; 34]) -> [bool; 34] {
        let mut solitary_tiles = [true; 34];
        for i in 0..34 {
            let tile = Tile::try_from(i as u8).unwrap();
            let tile_u8 = tile.as_u8();
            let tile_rank = tile_u8 % 9 + 1; //1-9

            if tehai[i] == 0 || tehai[i] > 1 {
                solitary_tiles[i] = false;
                continue;
            }

            if i < 27
                && (tile_rank > 1 && tehai[tile_u8 as usize - 1] > 0
                    || tile_rank > 2 && tehai[tile_u8 as usize - 2] > 0
                    || tile_rank < 8 && tehai[tile_u8 as usize + 2] > 0
                    || tile_rank < 9 && tehai[tile_u8 as usize + 1] > 0)
            {
                solitary_tiles[i] = false;
            }
        }
        solitary_tiles
    }
}
