use framework "Foundation"
use scripting additions

on run argv
    set operation to item 1 of argv
    set needle to item 2 of argv
    set resultLimit to (item 3 of argv) as integer
    set charLimit to (item 4 of argv) as integer

    set rows to current application's NSMutableArray's array()

    tell application "Notes"
        if operation is "search" then
            ignoring case
                set candidates to every note whose name contains needle
            end ignoring

        else if operation is "read" then
            set candidates to every note whose id is needle

        else
            set candidates to every note
        end if

        repeat with n in candidates
            set noteID to id of n
            set titleText to name of n
            set includeNote to false

            if operation is "list" then
                set includeNote to true

            else if operation is "search" then
                ignoring case
                    set includeNote to titleText contains needle
                end ignoring

            else if operation is "read" then
                set includeNote to noteID is needle
            end if

            if includeNote then
                set row to current application's NSMutableDictionary's dictionary()

                row's setObject:noteID forKey:"id"
                row's setObject:titleText forKey:"title"

                set noteFolder to get container of n
                set folderName to get name of noteFolder

                row's setObject:folderName forKey:"folder"

                if operation is "read" then
                    if password protected of n then
                        error "Locked note" number -10001
                    end if

                    set noteText to plaintext of n
                    set wasTruncated to (length of noteText) > charLimit

                    if wasTruncated then
                        set noteText to text 1 thru charLimit of noteText
                    end if

                    row's setObject:noteText forKey:"text"
                    row's setObject:wasTruncated forKey:"truncated"
                end if

                rows's addObject:row

                if (rows's |count|() as integer) ≥ resultLimit then
                    exit repeat
                end if
            end if
        end repeat
    end tell

    set jsonData to current application's NSJSONSerialization's ¬
        dataWithJSONObject:rows options:0 |error|:(missing value)

    return (current application's NSString's alloc()'s ¬
        initWithData:jsonData ¬
        encoding:(current application's NSUTF8StringEncoding)) as text
end run