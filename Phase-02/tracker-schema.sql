CREATE TABLE users (
    u_userkey integer PRIMARY KEY not null,
    u_name varchar(20) not null,
    u_email varchar(20) not null,
    u_password varchar(20) not null,
);

CREATE TABLE permit (
    p_permitkey integer PRIMARY KEY,
    p_userkey integer UNIQUE not null, -- I'm thinking since we have many one permit for a vehicle, we should do 1:M between users and permit
    p_vehicleskey integer not null,
    p_permittypekey integer not null,
    p_permitnum varchar(20) NOT NULL,
    p_issuedate date not null,
    p_expirationdate date not null,

    FOREIGN KEY (p_userkey) REFERENCES users(u_userkey),
    FOREIGN KEY (p_vehicleskey) REFERENCES vehicles(v_vehicleskey),
    FOREIGN KEY (p_permittypekey) REFERENCES permitType(pt_permittypekey)
);

CREATE TABLE permitType (
    pt_permittypekey integer PRIMARY KEY,
    pt_category varchar(20),
    pt_duration varchar(20)
);

CREATE TABLE vehicles (
    v_vehicleskey integer PRIMARY KEY,
    v_userkey integer not null,
    v_plateno varchar(7) not null,
    v_platestate varchar(20),
    v_maker varchar(20),
    v_model varchar(10),
    v_color varchar(10),

    FOREIGN KEY (v_userkey) REFERENCES users(u_userkey)
);

CREATE TABLE parkingHistory (
    ph_parkinghistkey integer PRIMARY KEY,
    ph_vehicleskey integer not null,
    ph_spotskey integer not null,
    ph_arrivaltime DATETIME,
    ph_departuretime DATETIME,

    FOREIGN KEY (ph_vehicleskey) REFERENCES vehicles(v_vehicleskey),
    FOREIGN KEY (ph_spotskey) REFERENCES spots(s_spotskey)
);

CREATE TABLE spots (
    s_spotskey integer PRIMARY KEY,
    s_zonekey integer not null,
    s_status BOOL,
    s_num varchar(5) not null,
    s_coordinates varchar(50), -- Thinking we probably don't need this
    s_isactive BOOL,

    FOREIGN KEY (s_zonekey) REFERENCES zone(z_zonekey)
);

CREATE TABLE zone (
    z_zonekey integer PRIMARY KEY,
    z_type varchar(10)
);

CREATE TABLE zoneAssignment (
    za_zonekey integer not null,
    za_lotkey integer not null,
    za_isactive BOOL,
    za_coordinates varchar(50),

    FOREIGN KEY (za_zonekey) REFERENCES zone(z_zonekey),
    FOREIGN KEY (za_lotkey) REFERENCES lot(l_lotkey)
);

CREATE TABLE lot (
    l_lotkey integer PRIMARY KEY,
    l_name varchar(20) not null,
    l_capacity integer not null,
    l_coordinates varchar(50)
);