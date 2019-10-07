SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET search_path = gn_imports, pg_catalog;
SET default_with_oids = false;


------------------------
--TABLES AND SEQUENCES--
------------------------

CREATE TABLE t_imports(
    id_import serial NOT NULL,
    format_source_file character varying(5),
    SRID integer,
    import_table character varying(255),
    id_dataset integer,
    id_mapping integer,
    date_create_import timestamp without time zone DEFAULT now(),
    date_update_import timestamp without time zone DEFAULT now(),
    date_end_import timestamp without time zone,
    source_count integer,
    import_count integer,
    taxa_count integer,
    date_min_data timestamp without time zone,
    date_max_data timestamp without time zone,
    step integer
);


CREATE TABLE cor_role_import(
    id_role integer NOT NULL,
    id_import integer NOT NULL
);


CREATE TABLE user_errors(
    id_error integer NOT NULL,
    error_type character varying(100) NOT NULL,
    name character varying(255) NOT NULL UNIQUE,
    description character varying(255) NOT NULL
);


CREATE TABLE cor_role_mapping(
    id_role integer NOT NULL,
    id_mapping integer NOT NULL
);


CREATE TABLE t_mappings_fields(
    id_match_fields serial NOT NULL,
    id_mapping integer NOT NULL,
    source_field character varying(255) NOT NULL,
    target_field character varying(255) NOT NULL
);


CREATE TABLE t_mappings_values(
    id_match_values serial NOT NULL,
    id_mapping integer NOT NULL,
    id_type_mapping integer NOT NULL,
    source_value character varying(255),
    id_target_value integer
);


CREATE TABLE bib_mappings(
    id_mapping serial NOT NULL,
    mapping_label character varying(255),
    active boolean
);


CREATE TABLE bib_type_mapping_values(
    id_type_mapping integer NOT NULL,
    mapping_type character varying(10)
);


CREATE TABLE bib_themes(
    id_theme integer,
    name_theme character varying(100) NOT NULL,
    fr_label character varying(100) NOT NULL,
    eng_label character varying(100),
    desc_theme character varying(1000),
    order_theme integer NOT NULL
);


CREATE TABLE bib_fields(
    id_field integer,
    name_field character varying(100) NOT NULL,
    fr_label character varying(100) NOT NULL,
    eng_label character varying(100),
    desc_field character varying(1000),
    type_field character varying(50),
    synthese_field boolean NOT NULL,
    mandatory boolean NOT NULL,
    autogenerate boolean NOT NULL,
    nomenclature boolean NOT NULL,
    id_theme integer NOT NULL,
    order_field integer NOT NULL
);



---------------
--PRIMARY KEY--
---------------

ALTER TABLE ONLY t_imports 
    ADD CONSTRAINT pk_gn_imports_t_imports PRIMARY KEY (id_import);

ALTER TABLE ONLY cor_role_import 
    ADD CONSTRAINT pk_cor_role_import PRIMARY KEY (id_role, id_import);

ALTER TABLE ONLY user_errors 
    ADD CONSTRAINT pk_user_errors PRIMARY KEY (id_error);

ALTER TABLE ONLY cor_role_mapping
    ADD CONSTRAINT pk_cor_role_mapping PRIMARY KEY (id_role, id_mapping);

ALTER TABLE ONLY t_mappings_fields
    ADD CONSTRAINT pk_t_mappings_fields PRIMARY KEY (id_match_fields);

ALTER TABLE ONLY t_mappings_values
    ADD CONSTRAINT pk_t_mappings_values PRIMARY KEY (id_match_values);

ALTER TABLE ONLY bib_mappings
    ADD CONSTRAINT pk_bib_mappings PRIMARY KEY (id_mapping);

ALTER TABLE ONLY bib_type_mapping_values
    ADD CONSTRAINT pk_bib_type_mapping_values PRIMARY KEY (id_type_mapping, mapping_type);

ALTER TABLE ONLY bib_themes
    ADD CONSTRAINT pk_bib_themes_id_theme PRIMARY KEY (id_theme);

ALTER TABLE ONLY bib_fields
    ADD CONSTRAINT pk_bib_fields_id_theme PRIMARY KEY (id_field);



---------------
--FOREIGN KEY--
---------------

ALTER TABLE ONLY t_imports
    ADD CONSTRAINT fk_gn_meta_t_datasets FOREIGN KEY (id_dataset) REFERENCES gn_meta.t_datasets(id_dataset) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY cor_role_import
    ADD CONSTRAINT fk_utilisateurs_t_roles FOREIGN KEY (id_role) REFERENCES utilisateurs.t_roles(id_role) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY cor_role_mapping
    ADD CONSTRAINT fk_utilisateurs_t_roles FOREIGN KEY (id_role) REFERENCES utilisateurs.t_roles(id_role) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY cor_role_mapping
    ADD CONSTRAINT fk_gn_imports_bib_mappings_id_mapping FOREIGN KEY (id_mapping) REFERENCES gn_imports.bib_mappings(id_mapping) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY t_mappings_fields
    ADD CONSTRAINT fk_gn_imports_bib_mappings_id_mapping FOREIGN KEY (id_mapping) REFERENCES gn_imports.bib_mappings(id_mapping) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY t_mappings_values
    ADD CONSTRAINT fk_gn_imports_bib_mappings_id_mapping FOREIGN KEY (id_mapping) REFERENCES gn_imports.bib_mappings(id_mapping) ON UPDATE CASCADE ON DELETE CASCADE;

--ALTER TABLE ONLY t_mappings_values
--    ADD CONSTRAINT fk_gn_imports_bib_type_mapping_values_id_type_mapping FOREIGN KEY (id_type_mapping) REFERENCES gn_imports.bib_type_mapping_values(id_type_mapping) ON UPDATE CASCADE ON DELETE CASCADE;

ALTER TABLE ONLY bib_fields
    ADD CONSTRAINT fk_gn_imports_bib_themes_id_theme FOREIGN KEY (id_theme) REFERENCES gn_imports.bib_themes(id_theme) ON UPDATE CASCADE ON DELETE CASCADE;


---------------------
--OTHER CONSTRAINTS--
---------------------

ALTER TABLE ONLY bib_type_mapping_values
    ADD CONSTRAINT check_mapping_type_in_bib_type_mapping_values CHECK (mapping_type IN ('NOMENCLATURE', 'ROLE'));



------------
--TRIGGERS--
------------
-- faire un trigger pour cor_role_mapping qui rempli quand create ou delete t_mappings.id_mapping?



-------------
--FUNCTIONS--
-------------


--------------
--INSERTIONS--
--------------

INSERT INTO user_errors (id_error, error_type, name, description) VALUES
	(1, 'invalid type error', 'invalid integer type', 'type integer invalide'),
	(2, 'invalid type error', 'invalid date type', 'type date invalide'),
	(3, 'invalid type error', 'invalid uuid type', 'type uuid invalide'),
	(4, 'invalid type error', 'invalid character varying length', 'champs de type character varying trop long'),
	(5, 'missing value error', 'missing value in required field', 'valeur manquante dans un champs obligatoire'),
	(6, 'missing value warning', 'warning : missing uuid type value', 'warning : valeur de type uuid manquante (non bloquant)'),
	(7, 'inconsistency error', 'date_min > date_max', 'date_min > date_max'),
	(8, 'inconsistency error', 'count_min > count_max', 'count_min > count_max'),
	(9, 'invalid value', 'invalid cd_nom', 'cd_nom invalide (absent de TaxRef)'),
	(10, 'inconsistency error', 'altitude min > altitude max', 'altitude min > altitude max'),
	(11, 'duplicates error', 'entitiy_source_pk_value duplicates', 'des valeurs de entity_source_pk_value ne sont pas uniques'),
	(12, 'invalid type error', 'invalid real type', 'type real invalide'),
	(13, 'inconsistency_error', 'inconsistent geographic coordinate', 'coordonnée géographique incohérente');


INSERT INTO bib_themes (id_theme, name_theme, fr_label, eng_label, desc_theme, order_theme) VALUES
	(1, 'general_info', 'Informations générales', '', '', 1),
    (2, 'statement_info', 'Informations de relevés', '', '', 2),
    (3, 'occurrence_sensitivity', 'Informations d''occurrences & sensibilité', '', '', 3),
    (4, 'enumeration', 'Dénombrements', '', '', 4),
    (5, 'validation', 'Détermination et validité', '', '', 5);


INSERT INTO bib_fields (id_field, name_field, fr_label, eng_label, desc_field, type_field, synthese_field, mandatory, autogenerate, nomenclature, id_theme, order_field) VALUES
	(1, 'entity_source_pk_value', 'Identifiant source', '', '', 'character varying', TRUE, FALSE, FALSE, FALSE, 1, 1),
	(2, 'unique_id_sinp', 'Identifiant SINP (uuid)', '', '', 'uuid', TRUE, FALSE, FALSE, FALSE, 1, 2),
	(3, 'unique_id_sinp_generate', 'Générer l''identifiant SINP', '', 'Génère automatiquement un identifiant de type uuid pour chaque observation', '', FALSE, FALSE, TRUE, FALSE, 1, 3), 
	(4, 'meta_create_date', 'Date de création de la donnée', '', '', 'timestamp without time zone', TRUE, FALSE, FALSE, FALSE, 1, 4),
	(5, 'meta_v_taxref', 'Version du référentiel taxonomique', '', '', 'character varying(50)', TRUE, FALSE, FALSE, FALSE, 1, 5),
	(6, 'meta_update_date', 'Date de mise à jour de la donnée', '', '', 'timestamp without time zone', TRUE, FALSE, FALSE, FALSE, 1, 6),
	(7, 'date_min', 'Date début', '', '', 'timestamp without time zone', TRUE, TRUE, FALSE, FALSE, 2, 1),
	(8, 'date_max', 'Date fin', '', '', 'timestamp without time zone', TRUE, FALSE, FALSE, FALSE, 2, 2),
	(9, 'altitude_min', 'Altitude min', '', '', 'integer', TRUE, FALSE, FALSE, FALSE, 2, 3),
	(10, 'altitude_max', 'Altitude max', '', '', 'integer', TRUE, FALSE, FALSE, FALSE, 2, 4),
	(11, 'altitudes_generate', 'Générer les altitudes', '', 'Génère automatiquement les altitudes pour chaque observation', '', FALSE, FALSE, TRUE, FALSE, 2, 5),
	(12, 'longitude', 'Longitude (coord x)', '', '', '', FALSE, TRUE, FALSE, FALSE, 2, 6),
	(13, 'latitude', 'Latitude (coord y)', '', '', '', FALSE, TRUE, FALSE, FALSE, 2, 7),
	(14, 'observers', 'Observateur(s)', '', '', 'character varying(1000)', TRUE, FALSE, FALSE, FALSE, 2, 8),
	(15, 'comment_description', 'Commentaire de relevé', '', '', 'text', TRUE, FALSE, FALSE, FALSE, 2, 9),
	(16, 'id_nomenclature_info_geo_type', 'Type d''information géographique', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 2, 10),
	(17, 'id_nomenclature_grp_typ', 'Type de relevé/regroupement', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 2, 11),
	(18, 'nom_cite', 'Nom du taxon cité', '', '', 'character varying(1000)', TRUE, TRUE, FALSE, FALSE, 3, 1),
	(19, 'cd_nom', 'Cd nom taxref', '', '', 'integer', TRUE, TRUE, FALSE, FALSE, 3, 2),
	(20, 'id_nomenclature_obs_meth', 'Méthode d''observation', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 3, 3),
	(21, 'id_nomenclature_bio_status', 'Statut biologique', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 3, 4),
	(22, 'id_nomenclature_bio_condition', 'Etat biologique', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 3, 5),
	(23, 'id_nomenclature_naturalness', 'Naturalité', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 3, 6),
	(24, 'comment_context', 'Commentaire d''occurrence', '', '', 'text', TRUE, FALSE, FALSE, FALSE, 3, 7),
	(25, 'id_nomenclature_sensitivity', 'Sensibilité', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 3, 8),
	(26, 'id_nomenclature_diffusion_level', 'Niveau de diffusion', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 3, 9),
	(27, 'id_nomenclature_blurring', 'Niveau de Floutage', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 3, 10),
	(28, 'id_nomenclature_life_stage', 'Stade de vie', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 4, 1),
	(29, 'id_nomenclature_sex', 'Sexe', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 4, 2),
	(30, 'id_nomenclature_type_count', 'Type du dénombrement', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 4, 3),
	(31, 'id_nomenclature_obj_count', 'Objet du dénombrement', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 4, 4),
	(32, 'count_min', 'Nombre minimal', '', '', 'integer', TRUE, FALSE, FALSE, FALSE, 4, 5),
	(33, 'count_max', 'Nombre maximal', '', '', 'integer', TRUE, FALSE, FALSE, FALSE, 4, 6),
	(34, 'id_nomenclature_determination_method', 'Méthode de détermination', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 5, 1),
	(35, 'determiner', 'Déterminateur', '', '', 'character varying(1000)', TRUE, FALSE, FALSE, FALSE, 5, 2),
	(36, 'id_digitiser', 'Auteur de la saisie', '', '', 'integer', TRUE, FALSE, FALSE, FALSE, 5, 3),
	(37, 'id_nomenclature_exist_proof', 'Existance d''une preuve', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 5, 4),
	(38, 'digital_proof', 'Preuve numérique', '', '', 'text', TRUE, FALSE, FALSE, FALSE, 5, 5),
	(39, 'non_digital_proof', 'Preuve non-numérique', '', '', 'text', TRUE, FALSE, FALSE, FALSE, 5, 6),
	(40, 'sample_number_proof', 'Identifiant de l''échantillon preuve', '', '', 'text', TRUE, FALSE, FALSE, FALSE, 5, 7),
	(41, 'id_nomenclature_valid_status', 'Statut de validation', '', '', 'integer', TRUE, FALSE, FALSE, TRUE, 5, 8),
	(42, 'validator', 'Validateur', '', '', 'character varying(1000)', TRUE, FALSE, FALSE, FALSE, 5, 9),
	(43, 'meta_validation_date', 'Date de validation', '', '', 'timestamp without time zone', TRUE, FALSE, FALSE, FALSE, 5, 10),
	(44, 'validation_comment', 'Commentaire de validation', '', '', 'text', TRUE, FALSE, FALSE, FALSE, 5, 11);

