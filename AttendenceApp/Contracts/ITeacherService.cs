using ServiceContracts.DTO.Teachers_DTO;

namespace Contracts
{
    /// <summary>
    /// This Represents Service For Teacher Entity
    /// </summary>
    public interface ITeacherService
    {
        /// <summary>
        /// Method for adding teacher
        /// </summary>
        /// <param name="addTeacherRequest"></param>
        /// <returns>newly created teacher object</returns>
        TeacherResponse AddTeacher(AddTeacherRequest addTeacherRequest);
        /// <summary>
        /// method for getting all teachers
        /// </summary>
        /// <returns>all teacher objects</returns>
        List<TeacherResponse> GetAllTeachers();
        /// <summary>
        /// method for getting teacher based on teacher ID
        /// </summary>
        /// <param name="id"></param>
        /// <returns></returns>
        TeacherResponse GetTeacher(Guid id);

        /// <summary>
        /// Method for updating teachers
        /// </summary>
        /// <param name="updateTeacherRequest"></param>
        /// <returns>updated teacher object</returns>
        TeacherResponse UpdateTeacher(UpdateTeacherRequest updateTeacherRequest);
        /// <summary>
        /// method for deleting teacher
        /// </summary>
        /// <param name="updateTeacherRequest"></param>
        /// <returns>whether the teacher is deleted or not</returns>
        bool DeleteTeacher(UpdateTeacherRequest updateTeacherRequest);
    }
}
