# Exemplar characters for the 2026 orthography

Exemplar characters are Survey Tool data in CLDR (`common/main/uz.xml`,
`<characters>`), so they are entered by vetters, not by a pull request. These
are the values to enter. Each proposed set was parsed with ICU 74.2's
UnicodeSet (main: 29 elements, index: 28); `tools/check_cldr.py` does not test
them.

## Current values (`uz`, CLDR main, 2026-11-08)

```
main:        [a b d e f g h i j k l m n o p q r s t u v x y z {oʻ} {gʻ} {sh} {ch} ʼ]
auxiliary:   [áàăâåäãā æ cç éèĕêëē íìĭîïī ñ óòŏôöøō œ úùŭûüū w ÿ]
index:       [A B D E F G H I J K L M N O P Q R S T U V X Y Z {Oʻ} {Gʻ} {Sh} {Ch}]
```

## Proposed: the 2026 orthography

The alphabet of Law No. O'RQ-1184: A B D E F G Ğ H I J K L M N O Ö P Q R S Ş Ç
T U V X Y Z — 28 letters — plus the tutuq belgisi ʼ (U+02BC).

```
main:        [a b d e f g ğ h i j k l m n o ö p q r s ş ç t u v x y z ʼ]
auxiliary:   [áàăâåäãā æ c éèĕêëē íìĭîïī ñ óòŏôøō œ úùŭûüū w ÿ]
index:       [A B D E F G Ğ H I J K L M N O Ö P Q R S Ş Ç T U V X Y Z]
```

- `main`: 28 letters and ʼ (29 elements).
- `auxiliary`: ç and ö leave it, because they are now letters of the alphabet.
  ō stays: drafts of the reform used it for ö.
- `index`: 28 letters, in the law's order. `index` is displayed in collation
  order, so it agrees with either collation option in `collation/`.

## Alternative: the transition years

While both Latin orthographies are in use, `main` can hold both. The index then
follows collation option A (`collation/uz.xml`): the 2026 letters in place,
the 1995 digraphs after Z.

```
main:        [a b d e f g ğ h i j k l m n o ö p q r s ş ç t u v x y z {oʻ} {gʻ} {sh} {ch} ʼ]
auxiliary:   [áàăâåäãā æ c éèĕêëē íìĭîïī ñ óòŏôøō œ úùŭûüū w ÿ]
index:       [A B D E F G Ğ H I J K L M N O Ö P Q R S Ş Ç T U V X Y Z {Oʻ} {Gʻ} {Sh} {Ch}]
```

Which of the two to enter, and when, depends on usage after 22 April 2027:
CLDR follows the form in common use.

## Cyrillic (`uz_Cyrl`) — unchanged

```
main:        [а б в г ғ д её ж з и й к қ л м н о п р с т уў ф х ҳ ч ш ъ э ю я]
auxiliary:   [ц щ ы ь]
```

Not part of this proposal. Note only that `ц` and `ь` are in the auxiliary set
although the Uzbek Cyrillic alphabet has 35 letters including both.
