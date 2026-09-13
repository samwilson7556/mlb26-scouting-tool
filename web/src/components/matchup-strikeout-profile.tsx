"use client";

import {
  AnalyticsMatchupKey,
  AnalyticsMatchupLocation,
  AnalyticsMatchupProfile,
  AnalyticsPlayerRow,
  AnalyticsTendencyItem,
} from "@/lib/api";


const MATCHUPS: Array<{
  key: AnalyticsMatchupKey;
  title: string;
  description: string;
}> = [
  {
    key: "RvR",
    title: "RvR",
    description: "RHP vs RHB",
  },
  {
    key: "RvL",
    title: "RvL",
    description: "RHP vs LHB",
  },
  {
    key: "LvR",
    title: "LvR",
    description: "LHP vs RHB",
  },
  {
    key: "LvL",
    title: "LvL",
    description: "LHP vs LHB",
  },
];


const LOCATION_GRID: AnalyticsMatchupLocation[][] = [
  [
    "high_in",
    "high",
    "high_away",
  ],
  [
    "inside",
    "middle",
    "outside",
  ],
  [
    "low_in",
    "low",
    "low_away",
  ],
];


type MatchupProfilePlayer = Pick<
  AnalyticsPlayerRow,
  | "player_name"
  | "plate_appearances"
  | "strikeouts"
  | "matchup_strikeout_profiles"
>;


export function MatchupStrikeoutTeamCard({
  title,
  players,
}: {
  title: string;
  players: MatchupProfilePlayer[];
}) {
  const player =
    aggregateMatchupPlayers(
      title,
      players
    );

  return (
    <MatchupStrikeoutProfileCard
      player={player}
    />
  );
}


const LOCATION_LABELS: Record<
  AnalyticsMatchupLocation,
  string
> = {
  high_in: "High / Inside",
  high: "High / Middle",
  high_away: "High / Away",
  inside: "Middle / Inside",
  middle: "Middle / Middle",
  outside: "Middle / Away",
  low_in: "Low / Inside",
  low: "Low / Middle",
  low_away: "Low / Away",
};


export function MatchupStrikeoutProfileCard({
  player,
}: {
  player: MatchupProfilePlayer;
}) {
  const profiles =
    player.matchup_strikeout_profiles;

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="font-black text-white">
            {player.player_name}
          </div>

          <div className="mt-1 text-xs text-slate-500">
            {player.plate_appearances} PA ·{" "}
            {player.strikeouts} K
          </div>
        </div>

        <div className="text-left text-xs sm:text-right">
          <div className="font-bold text-slate-300">
            {formatPercent(
              profiles.coverage_pct
            )} PA classified
          </div>

          <div className="mt-1 text-slate-600">
            {
              profiles
                .classified_plate_appearances
            }
            /{player.plate_appearances} PA ·{" "}
            {
              profiles
                .classified_strikeouts
            }
            /{player.strikeouts} K
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {MATCHUPS.map((matchup) => (
          <MatchupPanel
            key={matchup.key}
            title={matchup.title}
            description={
              matchup.description
            }
            profile={
              profiles.matchups[
                matchup.key
              ]
            }
          />
        ))}
      </div>
    </div>
  );
}


function MatchupPanel({
  title,
  description,
  profile,
}: {
  title: string;
  description: string;
  profile: AnalyticsMatchupProfile;
}) {
  const maxLocationCount = Math.max(
    0,
    ...Object.values(
      profile.location_counts
    )
  );

  return (
    <div className="rounded-xl border border-slate-800 bg-black/40 p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="text-sm font-black text-white">
            {title}
          </div>

          <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-600">
            {description}
          </div>
        </div>

        <div className="text-right">
          <div className="text-sm font-black text-white">
            {formatPercent(
              profile.strikeout_pct
            )}
          </div>

          <div className="text-[10px] text-slate-600">
            {profile.strikeouts} K /{" "}
            {profile.plate_appearances} PA
          </div>
        </div>
      </div>

      <BatterBox
        profile={profile}
        maxLocationCount={
          maxLocationCount
        }
      />

      <div className="mt-3 space-y-1.5 text-[11px]">
        <DetailRow
          label="Pitch"
          value={formatTopTendencies(
            profile.finishing_pitches,
            profile.with_finishing_pitch
          )}
        />

        <DetailRow
          label="Style"
          value={formatTopTendencies(
            profile.styles,
            profile.with_style
          )}
        />

        <DetailRow
          label="Located"
          value={
            profile.strikeouts > 0
              ? (
                `${profile.with_location}/`
                + `${profile.strikeouts} K`
              )
              : "N/A"
          }
        />
      </div>
    </div>
  );
}


function BatterBox({
  profile,
  maxLocationCount,
}: {
  profile: AnalyticsMatchupProfile;
  maxLocationCount: number;
}) {
  return (
    <div className="mt-3">
      <div className="grid grid-cols-[34px_repeat(3,minmax(0,1fr))] gap-1">
        <div />

        {[
          "INSIDE",
          "MIDDLE",
          "AWAY",
        ].map((label) => (
          <div
            key={label}
            className="pb-0.5 text-center text-[8px] font-black tracking-wide text-slate-600"
          >
            {label}
          </div>
        ))}

        {LOCATION_GRID.map(
          (row, rowIndex) => (
            <BatterBoxRow
              key={rowIndex}
              row={row}
              rowIndex={rowIndex}
              profile={profile}
              maxLocationCount={
                maxLocationCount
              }
            />
          )
        )}
      </div>
    </div>
  );
}


function BatterBoxRow({
  row,
  rowIndex,
  profile,
  maxLocationCount,
}: {
  row: AnalyticsMatchupLocation[];
  rowIndex: number;
  profile: AnalyticsMatchupProfile;
  maxLocationCount: number;
}) {
  const rowLabel = [
    "HIGH",
    "MID",
    "LOW",
  ][rowIndex];

  return (
    <>
      <div className="flex items-center justify-end pr-1 text-[8px] font-black tracking-wide text-slate-600">
        {rowLabel}
      </div>

      {row.map((location) => {
        const count =
          profile.location_counts[
            location
          ];

        const pct = (
          profile.with_location > 0
            ? (
              count
              / profile.with_location
              * 100
            )
            : 0
        );

        return (
          <div
            key={location}
            title={
              buildLocationTooltip(
                location,
                count,
                pct,
                profile
                  .location_pitch_counts[
                    location
                  ]
              )
            }
            className={
              "flex aspect-square min-h-10 "
              + "flex-col items-center justify-center "
              + "rounded border text-center "
              + heatClass(
                count,
                maxLocationCount
              )
            }
          >
            <div className="text-sm font-black">
              {count}
            </div>

            <div className="mt-0.5 text-[8px] font-semibold opacity-70">
              {
                profile.with_location > 0
                  ? `${pct.toFixed(0)}%`
                  : "—"
              }
            </div>
          </div>
        );
      })}
    </>
  );
}


function DetailRow({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="grid grid-cols-[46px_1fr] gap-2">
      <span className="font-bold text-slate-600">
        {label}
      </span>

      <span className="text-slate-300">
        {value}
      </span>
    </div>
  );
}


function heatClass(
  count: number,
  maxCount: number
): string {
  if (
    count <= 0
    || maxCount <= 0
  ) {
    return (
      "border-slate-800 "
      + "bg-slate-950 "
      + "text-slate-700"
    );
  }

  const ratio =
    count / maxCount;

  if (ratio >= 0.75) {
    return (
      "border-rose-400/40 "
      + "bg-rose-500/35 "
      + "text-rose-100"
    );
  }

  if (ratio >= 0.5) {
    return (
      "border-amber-400/30 "
      + "bg-amber-500/25 "
      + "text-amber-100"
    );
  }

  if (ratio >= 0.25) {
    return (
      "border-blue-400/30 "
      + "bg-blue-500/20 "
      + "text-blue-100"
    );
  }

  return (
    "border-slate-700 "
    + "bg-slate-800/70 "
    + "text-slate-300"
  );
}


function aggregateMatchupPlayers(
  title: string,
  players: MatchupProfilePlayer[]
): MatchupProfilePlayer {
  const totalPlateAppearances =
    players.reduce(
      (total, player) =>
        total
        + player.plate_appearances,
      0
    );

  const totalStrikeouts =
    players.reduce(
      (total, player) =>
        total
        + player.strikeouts,
      0
    );

  const classifiedPlateAppearances =
    players.reduce(
      (total, player) =>
        total
        + player
          .matchup_strikeout_profiles
          .classified_plate_appearances,
      0
    );

  const classifiedStrikeouts =
    players.reduce(
      (total, player) =>
        total
        + player
          .matchup_strikeout_profiles
          .classified_strikeouts,
      0
    );

  const matchups = Object.fromEntries(
    MATCHUPS.map(({ key }) => {
      const sourceProfiles =
        players.map(
          (player) =>
            player
              .matchup_strikeout_profiles
              .matchups[key]
        );

      const plateAppearances =
        sourceProfiles.reduce(
          (total, profile) =>
            total
            + profile
              .plate_appearances,
          0
        );

      const strikeouts =
        sourceProfiles.reduce(
          (total, profile) =>
            total
            + profile.strikeouts,
          0
        );

      const withFinishingPitch =
        sourceProfiles.reduce(
          (total, profile) =>
            total
            + profile
              .with_finishing_pitch,
          0
        );

      const withLocation =
        sourceProfiles.reduce(
          (total, profile) =>
            total
            + profile.with_location,
          0
        );

      const withStyle =
        sourceProfiles.reduce(
          (total, profile) =>
            total
            + profile.with_style,
          0
        );

      const locationCounts =
        Object.fromEntries(
          LOCATION_GRID
            .flat()
            .map((location) => [
              location,
              sourceProfiles.reduce(
                (total, profile) =>
                  total
                  + profile
                    .location_counts[
                      location
                    ],
                0
              ),
            ])
        ) as AnalyticsMatchupProfile[
          "location_counts"
        ];

      const locationPitchCounts =
        Object.fromEntries(
          LOCATION_GRID
            .flat()
            .map((location) => [
              location,
              aggregatePitchCounts(
                sourceProfiles.map(
                  (profile) =>
                    profile
                      .location_pitch_counts[
                        location
                      ]
                )
              ),
            ])
        ) as AnalyticsMatchupProfile[
          "location_pitch_counts"
        ];

      return [
        key,
        {
          plate_appearances:
            plateAppearances,
          strikeouts,
          strikeout_pct:
            calculatePercent(
              strikeouts,
              plateAppearances
            ),
          with_finishing_pitch:
            withFinishingPitch,
          with_location:
            withLocation,
          location_coverage_pct:
            calculatePercent(
              withLocation,
              strikeouts
            ),
          with_style: withStyle,
          location_counts:
            locationCounts,
          location_pitch_counts:
            locationPitchCounts,
          finishing_pitches:
            aggregateTendencies(
              sourceProfiles.map(
                (profile) =>
                  profile
                    .finishing_pitches
              ),
              withFinishingPitch
            ),
          locations:
            aggregateTendencies(
              sourceProfiles.map(
                (profile) =>
                  profile.locations
              ),
              withLocation
            ),
          styles:
            aggregateTendencies(
              sourceProfiles.map(
                (profile) =>
                  profile.styles
              ),
              withStyle
            ),
        },
      ];
    })
  ) as MatchupProfilePlayer[
    "matchup_strikeout_profiles"
  ]["matchups"];

  return {
    player_name: title,
    plate_appearances:
      totalPlateAppearances,
    strikeouts:
      totalStrikeouts,
    matchup_strikeout_profiles: {
      classified_plate_appearances:
        classifiedPlateAppearances,
      unclassified_plate_appearances:
        Math.max(
          0,
          totalPlateAppearances
          - classifiedPlateAppearances
        ),
      coverage_pct:
        calculatePercent(
          classifiedPlateAppearances,
          totalPlateAppearances
        ),
      classified_strikeouts:
        classifiedStrikeouts,
      unclassified_strikeouts:
        Math.max(
          0,
          totalStrikeouts
          - classifiedStrikeouts
        ),
      strikeout_coverage_pct:
        calculatePercent(
          classifiedStrikeouts,
          totalStrikeouts
        ),
      matchups,
    },
  };
}


function aggregatePitchCounts(
  groups: Array<Record<string, number>>
): Record<string, number> {
  const counts =
    new Map<string, number>();

  for (const group of groups) {
    for (
      const [
        pitchType,
        count,
      ]
      of Object.entries(group)
    ) {
      counts.set(
        pitchType,
        (
          counts.get(
            pitchType
          )
          ?? 0
        )
        + count
      );
    }
  }

  return Object.fromEntries(
    Array.from(
      counts.entries()
    ).sort(
      (left, right) =>
        (
          right[1]
          - left[1]
        )
        || left[0].localeCompare(
          right[0]
        )
    )
  );
}


function buildLocationTooltip(
  location: AnalyticsMatchupLocation,
  totalCount: number,
  pct: number,
  pitchCounts: Record<string, number>
): string {
  const lines = [
    (
      `${LOCATION_LABELS[location]}: `
      + `${totalCount} K`
      + (
        totalCount > 0
          ? ` (${pct.toFixed(1)}%)`
          : ""
      )
    ),
  ];

  if (totalCount <= 0) {
    return lines[0];
  }

  lines.push(
    "",
    "Finishing pitches:"
  );

  const entries =
    Object.entries(
      pitchCounts
    ).sort(
      (left, right) =>
        (
          right[1]
          - left[1]
        )
        || left[0].localeCompare(
          right[0]
        )
    );

  let knownPitchCount = 0;

  for (
    const [
      pitchType,
      count,
    ]
    of entries
  ) {
    knownPitchCount += count;

    lines.push(
      `${formatTendencyValue(
        pitchType
      )}: ${count}`
    );
  }

  const unknownPitchCount =
    Math.max(
      0,
      totalCount
      - knownPitchCount
    );

  if (unknownPitchCount > 0) {
    lines.push(
      `Unknown: ${unknownPitchCount}`
    );
  }

  return lines.join("\n");
}


function aggregateTendencies(
  groups: AnalyticsTendencyItem[][],
  knownCount: number
): AnalyticsTendencyItem[] {
  const counts =
    new Map<string, number>();

  for (const group of groups) {
    for (const item of group) {
      counts.set(
        item.value,
        (
          counts.get(
            item.value
          )
          ?? 0
        )
        + item.count
      );
    }
  }

  return Array.from(
    counts.entries()
  )
    .map(
      ([value, count]) => ({
        value,
        count,
        pct:
          knownCount > 0
            ? roundOneDecimal(
              count
              / knownCount
              * 100
            )
            : 0,
      })
    )
    .sort(
      (left, right) =>
        (
          right.count
          - left.count
        )
        || left.value.localeCompare(
          right.value
        )
    );
}


function calculatePercent(
  numerator: number,
  denominator: number
): number | null {
  if (denominator <= 0) {
    return null;
  }

  return roundOneDecimal(
    numerator
    / denominator
    * 100
  );
}


function roundOneDecimal(
  value: number
): number {
  return Math.round(
    value * 10
  ) / 10;
}


function formatTopTendencies(
  items: AnalyticsTendencyItem[],
  knownCount: number
): string {
  if (
    knownCount <= 0
    || items.length === 0
  ) {
    return "N/A";
  }

  return items
    .slice(0, 2)
    .map((item) => (
      `${formatTendencyValue(item.value)} `
      + `${item.count}/${knownCount}`
    ))
    .join(" · ");
}


function formatTendencyValue(
  value: string
): string {
  return value
    .split("_")
    .map((part) => (
      part.length === 0
        ? part
        : (
          part.charAt(0).toUpperCase()
          + part.slice(1)
        )
    ))
    .join(" ");
}


function formatPercent(
  value: number | null
): string {
  return value === null
    ? "N/A"
    : `${value.toFixed(1)}%`;
}
