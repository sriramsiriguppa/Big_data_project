import configparser


# CONFIG
config = configparser.ConfigParser()
config.read("dwh.cfg")

# DROP TABLES

drop_sql = "DROP TABLE IF EXISTS {};"

staging_events_table_drop = drop_sql.format("staging_events")
staging_songs_table_drop = drop_sql.format("staging_songs")
songplay_table_drop = drop_sql.format("songplays")
user_table_drop = drop_sql.format("users")
song_table_drop = drop_sql.format("songs")
artist_table_drop = drop_sql.format("artists")
time_table_drop = drop_sql.format("time_tables")

# CREATE TABLES

staging_events_table_create = """
CREATE TABLE IF NOT EXISTS staging_events (
    artist VARCHAR,
    auth VARCHAR NOT NULL,
    firstName VARCHAR,
    gender VARCHAR,
    itemInSession INT NOT NULL,
    lastName VARCHAR,
    length REAL,
    level VARCHAR NOT NULL,
    location VARCHAR,
    method VARCHAR NOT NULL,
    page VARCHAR NOT NULL,
    registration REAL,
    sessionId INT NOT NULL,
    song VARCHAR,
    status SMALLINT NOT NULL,
    ts BIGINT NOT NULL,
    userAgent VARCHAR,
    userId BIGINT
    );
"""

staging_songs_table_create = """
CREATE TABLE IF NOT EXISTS staging_songs (
    artist_id VARCHAR NOT NULL,
    artist_latitude REAL,
    artist_location VARCHAR,
    artist_longitude REAL,
    artist_name VARCHAR NOT NULL,
    duration REAL NOT NULL,
    num_songs INT NOT NULL,
    song_id VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    year INT NOT NULL
    );
"""

songplay_table_create = """
CREATE TABLE IF NOT EXISTS songplays (
    songplay_id BIGINT IDENTITY(1, 1),
    start_time TIMESTAMP SORTKEY NOT NULL,
    user_id VARCHAR DISTKEY NOT NULL,
    level VARCHAR NOT NULL,
    song_id VARCHAR NOT NULL,
    artist_id VARCHAR NOT NULL,
    session_id VARCHAR NOT NULL,
    location VARCHAR,
    user_agent VARCHAR,
    PRIMARY KEY (songplay_id),
    FOREIGN KEY (start_time) REFERENCES times,
    FOREIGN KEY (user_id) REFERENCES users,
    FOREIGN KEY (song_id) REFERENCES songs,
    FOREIGN KEY (artist_id) REFERENCES artists
    );
"""

user_table_create = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT DISTKEY NOT NULL,
    first_name VARCHAR,
    last_name VARCHAR,
    gender VARCHAR,
    level VARCHAR,
    PRIMARY KEY (user_id)
    );
"""

song_table_create = """
CREATE TABLE IF NOT EXISTS songs (
    song_id VARCHAR NOT NULL,
    title VARCHAR SORTKEY NOT NULL,
    artist_id VARCHAR NOT NULL,
    year VARCHAR NOT NULL,
    duration REAL NOT NULL,
    PRIMARY KEY (song_id),
    FOREIGN KEY (artist_id) REFERENCES artists
    )
    DISTSTYLE ALL;
"""

artist_table_create = """
CREATE TABLE IF NOT EXISTS artists (
    artist_id VARCHAR NOT NULL,
    name VARCHAR SORTKEY NOT NULL,
    location VARCHAR,
    latitude REAL,
    longitude REAL,
    PRIMARY KEY (artist_id)
    )
    DISTSTYLE ALL;
"""

time_table_create = """
CREATE TABLE IF NOT EXISTS times (
    start_time TIMESTAMP SORTKEY NOT NULL,
    hour SMALLINT,
    day SMALLINT,
    week SMALLINT,
    month SMALLINT,
    year INT,
    weekday SMALLINT,
    PRIMARY KEY(start_time)
    );
"""

# STAGING TABLES

staging_events_copy = (
    """
COPY staging_events
FROM '{s3_object}'
IAM_ROLE '{iam_role}'
JSON '{json_path}'
REGION '{region}';
"""
).format(
    s3_object=config["S3"]["LOG_DATA"],
    iam_role=config["IAM_ROLE"]["ARN"],
    json_path=config["S3"]["LOG_JSONPATH"],
    region=config["S3"]["REGION"],
)

staging_songs_copy = (
    """
COPY staging_songs
FROM '{s3_object}'
IAM_ROLE '{iam_role}'
JSON 'auto'
REGION '{region}';
"""
).format(
    s3_object=config["S3"]["SONG_DATA"],
    iam_role=config["IAM_ROLE"]["ARN"],
    region=config["S3"]["REGION"],
)

# FINAL TABLES

songplay_table_insert = """
INSERT INTO songplays (start_time, user_id, level, song_id, artist_id, session_id, location, user_agent)
SELECT DISTINCT
    DATEADD('milliseconds', e.ts, '1970-01-01') as start_time,
    e.userId,
    e.level,
    s.song_id,
    s.artist_id,
    e.sessionId,
    s.artist_location,
    e.userAgent
FROM staging_events e JOIN staging_songs s
ON e.song = s.title AND e.artist = s.artist_name
WHERE e.page = 'NextSong';
"""

user_table_insert = """
INSERT INTO users (user_id, first_name, last_name, gender, level)
SELECT DISTINCT se.userId, se.firstName, se.lastName, se.gender, se.level
FROM staging_events se
NATURAL JOIN
    (
    SELECT userId, MAX(ts) AS ts
    FROM staging_events
    GROUP BY userId
    ) grouped_staging_events;
"""


song_table_insert = """
INSERT INTO songs (song_id, title, artist_id, year, duration)
SELECT DISTINCT ss.song_id, ss.title, ss.artist_id, ss.year, ss.duration
FROM staging_songs ss
NATURAL JOIN
    (
    SELECT song_id, artist_id
    FROM songplays
    ) s;
"""


artist_table_insert = """
INSERT INTO artists (artist_id, name, location, longitude, latitude)
SELECT DISTINCT ss.artist_id,
    ss.artist_name AS name,
    ss.artist_location AS location,
    ss.artist_longitude AS longitude,
    ss. artist_latitude AS latitude
FROM staging_songs ss
NATURAL JOIN
    (
    SELECT artist_id
    FROM songplays
    ) s;
"""


time_table_insert = """
INSERT INTO times (start_time, hour, day, week, month, year, weekday)
SELECT DISTINCT
    start_time,
    EXTRACT (hour from start_time),
    EXTRACT (day from start_time),
    EXTRACT (week from start_time),
    EXTRACT (month from start_time),
    EXTRACT (year from start_time),
    EXTRACT (weekday from start_time)
FROM songplays;
"""

# QUERY LISTS

create_table_queries = [
    staging_events_table_create,
    staging_songs_table_create,
    time_table_create,
    user_table_create,
    artist_table_create,
    song_table_create,
    songplay_table_create,
]
drop_table_queries = [
    staging_events_table_drop,
    staging_songs_table_drop,
    songplay_table_drop,
    song_table_drop,
    artist_table_drop,
    user_table_drop,
    time_table_drop,
]
load_staging_table_queries = [staging_songs_copy, staging_events_copy]
insert_table_queries = [
    songplay_table_insert,
    user_table_insert,
    song_table_insert,
    artist_table_insert,
    time_table_insert,
]